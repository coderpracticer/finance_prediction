from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable

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

    def fetch_dataset(
        self,
        instrument: Instrument,
        progress: Callable[[str], None] | None = None,
    ) -> InstrumentDataset:
        source_config = self.config["sources"]
        warnings: list[str] = []
        prices: list[PriceBar] = []
        news: list[NewsItem] = []
        fundamentals = None

        try:
            if progress:
                progress(f"{instrument.symbol}: fetching Yahoo prices")
            prices = self.fetch_yahoo_prices(instrument, source_config["yahoo_chart_prices"])
            if progress:
                progress(f"{instrument.symbol}: Yahoo prices rows={len(prices)}")
        except Exception as exc:  # noqa: BLE001 - keep other sources usable.
            warnings.append(source_warning(instrument.symbol, "yahoo_chart_prices", exc))
            if progress:
                progress(f"{instrument.symbol}: Yahoo prices failed; trying fallback")
            try:
                if progress:
                    progress(f"{instrument.symbol}: fetching Alpha Vantage prices")
                prices = self.fetch_alpha_vantage_prices(
                    instrument,
                    source_config["alpha_vantage_daily"],
                )
                if progress:
                    progress(f"{instrument.symbol}: Alpha Vantage rows={len(prices)}")
            except Exception as alpha_exc:  # noqa: BLE001
                warnings.append(source_warning(instrument.symbol, "alpha_vantage_daily", alpha_exc))
            try:
                if not prices:
                    if progress:
                        progress(f"{instrument.symbol}: fetching Stooq prices")
                    prices = self.fetch_stooq_prices(instrument, source_config["stooq_prices"])
                    if progress:
                        progress(f"{instrument.symbol}: Stooq rows={len(prices)}")
            except Exception as fallback_exc:  # noqa: BLE001
                warnings.append(source_warning(instrument.symbol, "stooq_prices", fallback_exc))
        if not prices:
            cached_prices = self.load_cached_prices(instrument)
            if cached_prices is not None:
                prices, snapshot_path = cached_prices
                warnings.append(
                    f"{instrument.symbol}/price_cache: using cached snapshot {snapshot_path.name}"
                )
                if progress:
                    progress(
                        f"{instrument.symbol}: using cached price rows={len(prices)} "
                        f"from {snapshot_path.name}"
                    )
            elif progress:
                progress(f"{instrument.symbol}: no cached price snapshot found")

        try:
            if progress:
                progress(f"{instrument.symbol}: fetching Nasdaq RSS")
            news = self.fetch_nasdaq_news(instrument, source_config["nasdaq_stock_rss"])
            if progress:
                progress(f"{instrument.symbol}: Nasdaq RSS items={len(news)}")
        except Exception as exc:  # noqa: BLE001
            warnings.append(source_warning(instrument.symbol, "nasdaq_stock_rss", exc))
            if progress:
                progress(f"{instrument.symbol}: Nasdaq RSS failed: {type(exc).__name__}: {exc}")
            cached_news = self.load_cached_news(instrument)
            if cached_news is not None:
                news, snapshot_path = cached_news
                warnings.append(
                    f"{instrument.symbol}/news_cache: using cached snapshot {snapshot_path.name}"
                )
                if progress:
                    progress(
                        f"{instrument.symbol}: using cached news items={len(news)} "
                        f"from {snapshot_path.name}"
                    )

        if instrument.cik:
            try:
                if progress:
                    progress(f"{instrument.symbol}: fetching SEC companyfacts")
                fundamentals = self.fetch_sec_companyfacts(instrument, source_config["sec_companyfacts"])
                if progress:
                    progress(f"{instrument.symbol}: SEC metrics={fundamentals.metric_count}")
            except Exception as exc:  # noqa: BLE001
                warnings.append(source_warning(instrument.symbol, "sec_companyfacts", exc))
                if progress:
                    progress(f"{instrument.symbol}: SEC companyfacts failed: {type(exc).__name__}: {exc}")
                cached_fundamentals = self.load_cached_fundamentals(instrument)
                if cached_fundamentals is not None:
                    fundamentals, snapshot_path = cached_fundamentals
                    warnings.append(
                        f"{instrument.symbol}/fundamentals_cache: using cached snapshot "
                        f"{snapshot_path.name}"
                    )
                    if progress:
                        progress(
                            f"{instrument.symbol}: using cached SEC metrics="
                            f"{fundamentals.metric_count} from {snapshot_path.name}"
                        )
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
        return parse_yahoo_price_bars(payload)

    def fetch_alpha_vantage_prices(
        self,
        instrument: Instrument,
        config: dict[str, Any],
    ) -> list[PriceBar]:
        api_key_env = config.get("api_key_env", "ALPHA_VANTAGE_API_KEY")
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise RuntimeError(f"{api_key_env} is not set.")
        url = config["url_template"].format(symbol=instrument.symbol, api_key=api_key)
        payload = _fetch(url, {"Referer": "https://www.alphavantage.co/"})
        save_snapshot(self.raw_dir, "alpha_vantage_daily", instrument.symbol, payload, "json")
        data = json.loads(payload.decode("utf-8"))
        if "Error Message" in data:
            raise RuntimeError(str(data["Error Message"]))
        if "Information" in data:
            raise RuntimeError(str(data["Information"]))
        series = data.get("Time Series (Daily)")
        if not isinstance(series, dict) or not series:
            raise RuntimeError("Alpha Vantage returned no daily time series.")
        bars: list[PriceBar] = []
        for date_text, row in sorted(series.items()):
            bars.append(
                PriceBar(
                    timestamp=parse_date_timestamp(date_text),
                    open=parse_optional_float(row.get("1. open")),
                    high=parse_optional_float(row.get("2. high")),
                    low=parse_optional_float(row.get("3. low")),
                    close=float(row["4. close"]),
                    volume=parse_optional_float(row.get("5. volume")),
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
        return parse_sec_companyfacts_snapshot(payload)

    def fetch_nasdaq_news(self, instrument: Instrument, config: dict[str, Any]) -> list[NewsItem]:
        url = config["url_template"].format(symbol=instrument.symbol)
        payload = _fetch(url)
        save_snapshot(self.raw_dir, "nasdaq_stock_rss", instrument.symbol, payload, "xml")
        root = ET.fromstring(payload)
        return parse_rss_news(root)

    def load_cached_prices(self, instrument: Instrument) -> tuple[list[PriceBar], Path] | None:
        for source_name, suffix, parser in (
            ("yahoo_chart_prices", "json", parse_yahoo_price_bars),
            ("stooq_prices", "csv", lambda payload: parse_stooq_price_bars(payload.decode("utf-8"))),
        ):
            snapshot_path = self.latest_snapshot(source_name, instrument.symbol, suffix)
            if snapshot_path is None:
                continue
            try:
                prices = parser(snapshot_path.read_bytes())
            except Exception:  # noqa: BLE001 - ignore unusable stale cache candidates.
                continue
            if prices:
                return prices, snapshot_path
        return None

    def load_cached_news(self, instrument: Instrument) -> tuple[list[NewsItem], Path] | None:
        snapshot_path = self.latest_snapshot("nasdaq_stock_rss", instrument.symbol, "xml")
        if snapshot_path is None:
            return None
        try:
            root = ET.fromstring(snapshot_path.read_bytes())
            return parse_rss_news(root), snapshot_path
        except Exception:  # noqa: BLE001
            return None

    def load_cached_fundamentals(
        self,
        instrument: Instrument,
    ) -> tuple[FundamentalSnapshot, Path] | None:
        snapshot_path = self.latest_snapshot("sec_companyfacts", instrument.symbol, "json")
        if snapshot_path is None:
            return None
        try:
            return parse_sec_companyfacts_snapshot(snapshot_path.read_bytes()), snapshot_path
        except Exception:  # noqa: BLE001
            return None

    def latest_snapshot(self, source_name: str, symbol: str, suffix: str) -> Path | None:
        safe_source = safe_snapshot_name(source_name)
        safe_symbol = safe_snapshot_name(symbol)
        matches: list[Path] = []
        pattern = f"*_{safe_source}_{safe_symbol}.{suffix}"
        for root in self.cache_roots():
            matches.extend(root.glob(pattern))
        matches = sorted(set(matches), key=lambda path: path.stat().st_mtime, reverse=True)
        return matches[0] if matches else None

    def cache_roots(self) -> list[Path]:
        roots = [self.raw_dir]
        if self.raw_dir.parent.name == "raw" and self.raw_dir.parent.exists():
            roots.extend(path for path in self.raw_dir.parent.iterdir() if path.is_dir())
        return list(dict.fromkeys(roots))


def _list_get(values: list[Any] | None, index: int) -> Any:
    if values is None or index >= len(values):
        return None
    return values[index]


def _xml_text(item: ET.Element, tag: str) -> str | None:
    node = item.find(tag)
    if node is None or node.text is None:
        return None
    return node.text.strip()


def parse_yahoo_price_bars(payload: bytes) -> list[PriceBar]:
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
    if not bars:
        raise RuntimeError("Yahoo chart returned no usable price bars.")
    return bars


def parse_stooq_price_bars(text: str) -> list[PriceBar]:
    import csv

    bars: list[PriceBar] = []
    for row in csv.DictReader(text.splitlines()):
        close = row.get("Close")
        if not close:
            continue
        date_text = row.get("Date")
        timestamp = parse_date_timestamp(date_text) if date_text else 0
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


def parse_rss_news(root: ET.Element) -> list[NewsItem]:
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


def parse_sec_companyfacts_snapshot(payload: bytes) -> FundamentalSnapshot:
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


def parse_optional_float(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)


def parse_date_timestamp(date_text: str) -> int:
    from datetime import datetime

    return int(datetime.strptime(date_text, "%Y-%m-%d").timestamp())


def source_warning(symbol: str, source_name: str, exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"{symbol}/{source_name}: HTTP {exc.code} {exc.reason}"
    return f"{symbol}/{source_name}: {type(exc).__name__}: {exc}"


def safe_snapshot_name(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")
