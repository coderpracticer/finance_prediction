from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from backend.app.data_sources.spike import (
    DEFAULT_SEC_USER_AGENT,
    DEFAULT_TIMEOUT_SECONDS,
    load_config,
    save_snapshot,
)
from backend.app.models.schemas import (
    FundamentalSnapshot,
    Instrument,
    InstrumentDataset,
    NewsItem,
    PriceBar,
)


def _fetch(url: str, headers: dict[str, str] | None = None) -> bytes:
    request_headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, application/rss+xml, text/xml, text/csv, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://finance.yahoo.com/",
    }
    request_headers.update(headers or {})
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        return response.read()


class DataSourceClient:
    def __init__(self, config_path: Path, raw_dir: Path) -> None:
        self.config = load_config(config_path)
        self.raw_dir = raw_dir

    def universe(self) -> list[Instrument]:
        return [Instrument(**item) for item in self.config["universe"]]

    def fetch_dataset(self, instrument: Instrument) -> InstrumentDataset:
        source_config = self.config["sources"]
        warnings: list[str] = []
        prices: list[PriceBar] = []
        news: list[NewsItem] = []
        fundamentals = None

        try:
            prices = self.fetch_yahoo_prices(instrument, source_config["yahoo_chart_prices"])
        except Exception as exc:  # noqa: BLE001 - keep other sources usable.
            warnings.append(source_warning(instrument.symbol, "yahoo_chart_prices", exc))
            try:
                prices = self.fetch_stooq_prices(instrument, source_config["stooq_prices"])
            except Exception as fallback_exc:  # noqa: BLE001
                warnings.append(source_warning(instrument.symbol, "stooq_prices", fallback_exc))

        try:
            news = self.fetch_nasdaq_news(instrument, source_config["nasdaq_stock_rss"])
        except Exception as exc:  # noqa: BLE001
            warnings.append(source_warning(instrument.symbol, "nasdaq_stock_rss", exc))

        if instrument.cik:
            try:
                fundamentals = self.fetch_sec_companyfacts(instrument, source_config["sec_companyfacts"])
            except Exception as exc:  # noqa: BLE001
                warnings.append(source_warning(instrument.symbol, "sec_companyfacts", exc))
        return InstrumentDataset(
            instrument=instrument,
            prices=prices,
            news=news,
            fundamentals=fundamentals,
            warnings=warnings,
        )

    def fetch_yahoo_prices(self, instrument: Instrument, config: dict[str, Any]) -> list[PriceBar]:
        urls = [
            config["url_template"].format(symbol=instrument.symbol),
            config["url_template"].format(symbol=instrument.symbol).replace(
                "query1.finance.yahoo.com",
                "query2.finance.yahoo.com",
            ),
        ]
        last_error: Exception | None = None
        payload: bytes | None = None
        for url in urls:
            try:
                payload = _fetch(url)
                break
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {403, 429, 502, 503}:
                    raise
        if payload is None:
            if last_error is not None:
                raise last_error
            raise RuntimeError("No Yahoo chart payload returned.")
        save_snapshot(self.raw_dir, "yahoo_chart_prices", instrument.symbol, payload, "json")
        data = json.loads(payload.decode("utf-8"))
        results = data.get("chart", {}).get("result") or []
        if not results:
            raise RuntimeError("Yahoo chart returned no result.")
        result = results[0]
        timestamps = result.get("timestamp") or []
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        bars: list[PriceBar] = []
        for index, timestamp in enumerate(timestamps):
            close = _list_get(quote.get("close"), index)
            if close is None:
                continue
            bars.append(
                PriceBar(
                    timestamp=timestamp,
                    open=_list_get(quote.get("open"), index),
                    high=_list_get(quote.get("high"), index),
                    low=_list_get(quote.get("low"), index),
                    close=close,
                    volume=_list_get(quote.get("volume"), index),
                )
            )
        return bars

    def fetch_stooq_prices(self, instrument: Instrument, config: dict[str, Any]) -> list[PriceBar]:
        if not instrument.stooq_symbol:
            raise RuntimeError("Instrument has no stooq_symbol.")
        url = config["url_template"].format(stooq_symbol=instrument.stooq_symbol)
        payload = _fetch(url)
        text = payload.decode("utf-8", errors="replace")
        if text.lstrip().lower().startswith("<!doctype html") or text.lstrip().lower().startswith(
            "<html"
        ):
            raise RuntimeError("Stooq returned an HTML verification page.")
        save_snapshot(self.raw_dir, "stooq_prices", instrument.symbol, payload, "csv")
        return parse_stooq_price_bars(text)

    def fetch_sec_companyfacts(
        self,
        instrument: Instrument,
        config: dict[str, Any],
    ) -> FundamentalSnapshot:
        url = config["url_template"].format(cik=instrument.cik)
        user_agent_env = config.get("user_agent_env", "SEC_USER_AGENT")
        payload = _fetch(url, {"User-Agent": os.getenv(user_agent_env, DEFAULT_SEC_USER_AGENT)})
        save_snapshot(self.raw_dir, "sec_companyfacts", instrument.symbol, payload, "json")
        data = json.loads(payload.decode("utf-8"))
        us_gaap = data.get("facts", {}).get("us-gaap", {})
        metrics = sorted(us_gaap.keys())
        return FundamentalSnapshot(
            metric_count=len(metrics),
            available_metrics=metrics[:50],
            has_revenue="Revenues" in us_gaap,
            has_net_income="NetIncomeLoss" in us_gaap,
            has_eps="EarningsPerShareDiluted" in us_gaap,
        )

    def fetch_nasdaq_news(self, instrument: Instrument, config: dict[str, Any]) -> list[NewsItem]:
        url = config["url_template"].format(symbol=instrument.symbol)
        payload = _fetch(url)
        save_snapshot(self.raw_dir, "nasdaq_stock_rss", instrument.symbol, payload, "xml")
        root = ET.fromstring(payload)
        items: list[NewsItem] = []
        for item in root.findall(".//item")[:20]:
            items.append(
                NewsItem(
                    title=_xml_text(item, "title") or "Untitled",
                    link=_xml_text(item, "link"),
                    published_at=_xml_text(item, "pubDate"),
                    summary=_xml_text(item, "description"),
                )
            )
        return items


def _list_get(values: list[Any] | None, index: int) -> Any:
    if values is None or index >= len(values):
        return None
    return values[index]


def _xml_text(item: ET.Element, tag: str) -> str | None:
    node = item.find(tag)
    if node is None or node.text is None:
        return None
    return node.text.strip()


def parse_stooq_price_bars(text: str) -> list[PriceBar]:
    import csv
    from datetime import datetime

    bars: list[PriceBar] = []
    for row in csv.DictReader(text.splitlines()):
        close = row.get("Close")
        if not close:
            continue
        date_text = row.get("Date")
        timestamp = 0
        if date_text:
            timestamp = int(datetime.strptime(date_text, "%Y-%m-%d").timestamp())
        bars.append(
            PriceBar(
                timestamp=timestamp,
                open=parse_optional_float(row.get("Open")),
                high=parse_optional_float(row.get("High")),
                low=parse_optional_float(row.get("Low")),
                close=float(close),
                volume=parse_optional_float(row.get("Volume")),
            )
        )
    if not bars:
        raise RuntimeError("Stooq returned no usable price rows.")
    return bars


def parse_optional_float(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)


def source_warning(symbol: str, source_name: str, exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"{symbol}/{source_name}: HTTP {exc.code} {exc.reason}"
    return f"{symbol}/{source_name}: {type(exc).__name__}: {exc}"
