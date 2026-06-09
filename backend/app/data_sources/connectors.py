from __future__ import annotations

import json
import os
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
        "User-Agent": "Mozilla/5.0 (compatible; FinancialResearchAgent/0.1)",
        "Accept": "application/json, application/rss+xml, text/xml, */*",
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
        prices = self.fetch_yahoo_prices(instrument, source_config["yahoo_chart_prices"])
        news = self.fetch_nasdaq_news(instrument, source_config["nasdaq_stock_rss"])
        fundamentals = None
        if instrument.cik:
            fundamentals = self.fetch_sec_companyfacts(instrument, source_config["sec_companyfacts"])
        return InstrumentDataset(
            instrument=instrument,
            prices=prices,
            news=news,
            fundamentals=fundamentals,
        )

    def fetch_yahoo_prices(self, instrument: Instrument, config: dict[str, Any]) -> list[PriceBar]:
        url = config["url_template"].format(symbol=instrument.symbol)
        payload = _fetch(url)
        save_snapshot(self.raw_dir, "yahoo_chart_prices", instrument.symbol, payload, "json")
        data = json.loads(payload.decode("utf-8"))
        result = (data.get("chart", {}).get("result") or [])[0]
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
