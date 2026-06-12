from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from html import unescape
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


def _fetch(
    url: str,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> bytes:
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
    request = urllib.request.Request(url, data=data, headers=request_headers)
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        return response.read()


class SkipPriceNetworkFetch(Exception):
    """Used internally when a higher-priority local price source already succeeded."""


class DataSourceClient:
    def __init__(
        self,
        config_path: Path,
        raw_dir: Path,
        price_csv_dir: Path | None = None,
    ) -> None:
        self.config = load_config(config_path)
        self.raw_dir = raw_dir
        self.price_csv_dir = price_csv_dir

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

        local_prices = self.load_local_csv_prices(instrument)
        if local_prices is not None:
            prices, csv_path = local_prices
            warnings.append(f"{instrument.symbol}/price_local_csv: using {csv_path}")
            if progress:
                progress(
                    f"{instrument.symbol}: using local CSV price rows={len(prices)} from {csv_path}"
                )

        try:
            if not prices and source_enabled(source_config, "eastmoney_kline_prices"):
                if progress:
                    progress(f"{instrument.symbol}: fetching Eastmoney kline prices")
                prices = self.fetch_eastmoney_kline_prices(
                    instrument,
                    source_config["eastmoney_kline_prices"],
                )
                if progress:
                    progress(f"{instrument.symbol}: Eastmoney kline rows={len(prices)}")
        except Exception as eastmoney_exc:  # noqa: BLE001
            warnings.append(source_warning(instrument.symbol, "eastmoney_kline_prices", eastmoney_exc))

        try:
            if prices:
                raise SkipPriceNetworkFetch()
            if not source_enabled(source_config, "yahoo_chart_prices"):
                raise RuntimeError("yahoo_chart_prices is disabled.")
            if progress:
                progress(f"{instrument.symbol}: fetching Yahoo prices")
            prices = self.fetch_yahoo_prices(instrument, source_config["yahoo_chart_prices"])
            if progress:
                progress(f"{instrument.symbol}: Yahoo prices rows={len(prices)}")
        except SkipPriceNetworkFetch:
            pass
        except Exception as exc:  # noqa: BLE001 - keep other sources usable.
            warnings.append(source_warning(instrument.symbol, "yahoo_chart_prices", exc))
            if progress:
                progress(f"{instrument.symbol}: Yahoo prices failed; trying fallback")
            try:
                if not prices and source_enabled(source_config, "nasdaq_historical_prices"):
                    if progress:
                        progress(f"{instrument.symbol}: fetching Nasdaq historical prices")
                    prices = self.fetch_nasdaq_historical_prices(
                        instrument,
                        source_config["nasdaq_historical_prices"],
                    )
                    if progress:
                        progress(f"{instrument.symbol}: Nasdaq historical rows={len(prices)}")
            except Exception as nasdaq_price_exc:  # noqa: BLE001
                warnings.append(
                    source_warning(instrument.symbol, "nasdaq_historical_prices", nasdaq_price_exc)
            )
            try:
                if not prices and source_enabled(source_config, "alpha_vantage_daily"):
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
                if not prices and source_enabled(source_config, "stooq_prices"):
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

        if source_enabled(source_config, "instrument_config_metadata"):
            fundamentals = self.build_instrument_config_metadata(instrument)
            if progress:
                progress(
                    f"{instrument.symbol}: loaded config metadata metrics="
                    f"{fundamentals.metric_count}"
                )

        if source_enabled(source_config, "instrument_research_context"):
            context_items = self.build_instrument_research_context(instrument)
            news.extend(context_items)
            if progress:
                progress(
                    f"{instrument.symbol}: loaded configured research context "
                    f"items={len(context_items)}"
                )

        if source_enabled(source_config, "cninfo_announcements"):
            try:
                if progress:
                    progress(f"{instrument.symbol}: fetching CNInfo announcements")
                news.extend(
                    self.fetch_cninfo_announcements(
                        instrument,
                        source_config["cninfo_announcements"],
                    )
                )
                if progress:
                    progress(f"{instrument.symbol}: CNInfo announcement items={len(news)}")
            except Exception as exc:  # noqa: BLE001
                warnings.append(source_warning(instrument.symbol, "cninfo_announcements", exc))
                if progress:
                    progress(
                        f"{instrument.symbol}: CNInfo announcements failed: "
                        f"{type(exc).__name__}: {exc}"
                    )

        if source_enabled(source_config, "nasdaq_stock_rss"):
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

        if instrument.cik and source_enabled(source_config, "sec_companyfacts"):
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

    def build_instrument_config_metadata(self, instrument: Instrument) -> FundamentalSnapshot:
        details = {
            key: value
            for key, value in {
                "asset_type": instrument.asset_type,
                "exchange": instrument.exchange,
                "category": instrument.category,
                "tracking_index": instrument.tracking_index,
                "fund_company": instrument.fund_company,
                "theme": instrument.theme,
                "policy_watch": instrument.policy_watch,
                "risk_profile": instrument.risk_profile,
            }.items()
            if value
        }
        return FundamentalSnapshot(
            metric_count=len(details),
            available_metrics=list(details.keys()),
            details=details,
        )

    def build_instrument_research_context(self, instrument: Instrument) -> list[NewsItem]:
        if not any([instrument.theme, instrument.tracking_index, instrument.policy_watch]):
            return []
        title = f"{instrument.name}研究上下文：{instrument.theme or instrument.tracking_index}"
        summary_parts = [
            "这是系统配置的非价格研究线索，不是实时新闻或公告。",
        ]
        if instrument.tracking_index:
            summary_parts.append(f"跟踪指数：{instrument.tracking_index}。")
        if instrument.theme:
            summary_parts.append(f"主题定位：{instrument.theme}。")
        if instrument.policy_watch:
            summary_parts.append(f"后续重点观察：{instrument.policy_watch}。")
        if instrument.risk_profile:
            summary_parts.append(f"风险画像：{instrument.risk_profile}。")
        return [
            NewsItem(
                title=title,
                summary="".join(summary_parts),
                source="配置研究上下文",
                category="research_context",
            )
        ]

    def fetch_eastmoney_kline_prices(
        self,
        instrument: Instrument,
        config: dict[str, Any],
    ) -> list[PriceBar]:
        secid = resolve_eastmoney_secid(instrument)
        url = config["url_template"].format(
            secid=secid,
            klt=config.get("klt", "101"),
            fqt=config.get("fqt", "1"),
            beg=config.get("beg", "20160101"),
            end=config.get("end", "20500101"),
        )
        payload = _fetch(
            url,
            {
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://quote.eastmoney.com/",
            },
        )
        save_snapshot(self.raw_dir, "eastmoney_kline_prices", instrument.symbol, payload, "json")
        return parse_eastmoney_kline_prices(payload)

    def load_local_csv_prices(self, instrument: Instrument) -> tuple[list[PriceBar], Path] | None:
        if self.price_csv_dir is None:
            return None
        candidates = [
            self.price_csv_dir / f"{instrument.symbol}.csv",
            self.price_csv_dir / f"{instrument.symbol.lower()}.csv",
            self.price_csv_dir / f"{instrument.symbol.upper()}.csv",
        ]
        for path in candidates:
            if not path.exists():
                continue
            prices = parse_local_price_csv(path.read_text(encoding="utf-8-sig"))
            if prices:
                return prices, path
        return None

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

    def fetch_nasdaq_historical_prices(
        self,
        instrument: Instrument,
        config: dict[str, Any],
    ) -> list[PriceBar]:
        today = datetime.now(UTC).date()
        lookback_days = int(config.get("lookback_days", 365))
        start = today - timedelta(days=lookback_days)
        asset_class = config.get("asset_class", "stocks")
        url = config["url_template"].format(
            symbol=instrument.symbol.upper(),
            asset_class=asset_class,
            fromdate=start.isoformat(),
            todate=today.isoformat(),
        )
        payload = _fetch(
            url,
            {
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.nasdaq.com",
                "Referer": f"https://www.nasdaq.com/market-activity/stocks/{instrument.symbol.lower()}/historical",
            },
        )
        save_snapshot(self.raw_dir, "nasdaq_historical_prices", instrument.symbol, payload, "json")
        return parse_nasdaq_historical_prices(payload)

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

    def fetch_cninfo_announcements(
        self,
        instrument: Instrument,
        config: dict[str, Any],
    ) -> list[NewsItem]:
        items: list[NewsItem] = []
        combined_payloads: list[dict[str, Any]] = []
        last_error: Exception | None = None
        for form in build_cninfo_query_forms(instrument, int(config.get("page_size", 5))):
            try:
                payload = self.fetch_cninfo_form(config["url"], form)
                combined_payloads.append(
                    {
                        "form": form,
                        "payload": json.loads(payload.decode("utf-8")),
                    }
                )
                items.extend(parse_cninfo_announcements(payload))
            except Exception as exc:  # noqa: BLE001 - try the remaining query shapes.
                last_error = exc
        if combined_payloads:
            save_snapshot(
                self.raw_dir,
                "cninfo_announcements",
                instrument.symbol,
                json.dumps(combined_payloads, ensure_ascii=False).encode("utf-8"),
                "json",
            )
        elif last_error is not None:
            raise last_error
        return dedupe_news_items(items)[: int(config.get("page_size", 5))]

    def fetch_cninfo_form(self, url: str, form: dict[str, str]) -> bytes:
        return _fetch(
            url,
            headers={
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": "https://www.cninfo.com.cn",
                "Referer": "https://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
            },
            data=urllib.parse.urlencode(form).encode("utf-8"),
        )

    def fetch_nasdaq_news(self, instrument: Instrument, config: dict[str, Any]) -> list[NewsItem]:
        url = config["url_template"].format(symbol=instrument.symbol)
        payload = _fetch(url)
        save_snapshot(self.raw_dir, "nasdaq_stock_rss", instrument.symbol, payload, "xml")
        root = ET.fromstring(payload)
        return parse_rss_news(root)

    def load_cached_prices(self, instrument: Instrument) -> tuple[list[PriceBar], Path] | None:
        for source_name, suffix, parser in (
            ("eastmoney_kline_prices", "json", parse_eastmoney_kline_prices),
            ("yahoo_chart_prices", "json", parse_yahoo_price_bars),
            ("nasdaq_historical_prices", "json", parse_nasdaq_historical_prices),
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


def build_cninfo_query_forms(instrument: Instrument, page_size: int) -> list[dict[str, str]]:
    exchange = (instrument.exchange or "").upper()
    column = "sse" if exchange == "SH" else "szse" if exchange == "SZ" else ""
    base = {
        "stock": instrument.symbol,
        "searchkey": "",
        "plate": "",
        "category": "",
        "trade": "",
        "column": column,
        "pageNum": "1",
        "pageSize": str(page_size),
        "tabName": "fulltext",
        "sortName": "",
        "sortType": "",
        "limit": "",
        "seDate": "",
    }
    forms = [base]
    for searchkey, search_column in (
        (instrument.symbol, "fund"),
        (instrument.name, "fund"),
        (instrument.tracking_index or "", "fund"),
        (instrument.name, ""),
    ):
        if not searchkey:
            continue
        form = dict(base)
        form["stock"] = ""
        form["searchkey"] = searchkey
        form["column"] = search_column
        forms.append(form)
    unique_forms: list[dict[str, str]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for form in forms:
        key = tuple(sorted(form.items()))
        if key in seen:
            continue
        seen.add(key)
        unique_forms.append(form)
    return unique_forms


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


def parse_nasdaq_historical_prices(payload: bytes) -> list[PriceBar]:
    data = json.loads(payload.decode("utf-8"))
    rows = (
        data.get("data", {})
        .get("tradesTable", {})
        .get("rows", [])
    )
    bars: list[PriceBar] = []
    for row in rows:
        date_text = row.get("date")
        close = parse_market_number(row.get("close"))
        if not date_text or close is None:
            continue
        bars.append(
            PriceBar(
                timestamp=parse_flexible_timestamp(date_text),
                open=parse_market_number(row.get("open")),
                high=parse_market_number(row.get("high")),
                low=parse_market_number(row.get("low")),
                close=close,
                volume=parse_market_number(row.get("volume")),
            )
        )
    bars.sort(key=lambda bar: bar.timestamp)
    if not bars:
        raise RuntimeError("Nasdaq historical API returned no usable price rows.")
    return bars


def parse_eastmoney_kline_prices(payload: bytes) -> list[PriceBar]:
    data = json.loads(payload.decode("utf-8"))
    klines = data.get("data", {}).get("klines")
    if not isinstance(klines, list) or not klines:
        raise RuntimeError("Eastmoney kline API returned no usable kline rows.")
    bars: list[PriceBar] = []
    for item in klines:
        if not isinstance(item, str):
            continue
        parts = item.split(",")
        if len(parts) < 7:
            continue
        date_text, open_text, close_text, high_text, low_text, volume_text = parts[:6]
        close = parse_optional_float(close_text)
        if close is None:
            continue
        bars.append(
            PriceBar(
                timestamp=parse_date_timestamp(date_text),
                open=parse_optional_float(open_text),
                high=parse_optional_float(high_text),
                low=parse_optional_float(low_text),
                close=close,
                volume=parse_optional_float(volume_text),
            )
        )
    bars.sort(key=lambda bar: bar.timestamp)
    if not bars:
        raise RuntimeError("Eastmoney kline API returned no parseable price rows.")
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


def parse_local_price_csv(text: str) -> list[PriceBar]:
    import csv

    bars: list[PriceBar] = []
    for row in csv.DictReader(text.splitlines()):
        normalized = {key.lower(): value for key, value in row.items() if key is not None}
        close = normalized.get("close")
        date_text = normalized.get("date") or normalized.get("timestamp")
        if not close or not date_text:
            continue
        bars.append(
            PriceBar(
                timestamp=parse_flexible_timestamp(date_text),
                open=parse_optional_float(normalized.get("open")),
                high=parse_optional_float(normalized.get("high")),
                low=parse_optional_float(normalized.get("low")),
                close=float(close),
                volume=parse_optional_float(normalized.get("volume")),
            )
        )
    bars.sort(key=lambda bar: bar.timestamp)
    if not bars:
        raise RuntimeError("Local price CSV returned no usable rows.")
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


def parse_cninfo_announcements(payload: bytes) -> list[NewsItem]:
    data = json.loads(payload.decode("utf-8"))
    rows = data.get("announcements") or []
    items: list[NewsItem] = []
    for row in rows[:10]:
        if not isinstance(row, dict):
            continue
        title = clean_html_text(str(row.get("announcementTitle") or "")).strip()
        if not title:
            continue
        adjunct_url = row.get("adjunctUrl")
        link = f"https://static.cninfo.com.cn/{adjunct_url}" if adjunct_url else None
        published_at = None
        timestamp = row.get("announcementTime")
        if isinstance(timestamp, (int, float)):
            published_at = datetime.fromtimestamp(timestamp / 1000, UTC).date().isoformat()
        items.append(
            NewsItem(
                title=title,
                link=link,
                published_at=published_at,
                source="巨潮资讯",
                category="announcement",
            )
        )
    return items


def dedupe_news_items(items: list[NewsItem]) -> list[NewsItem]:
    deduped: list[NewsItem] = []
    seen: set[tuple[str, str | None]] = set()
    for item in items:
        key = (item.title, item.link)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


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


def clean_html_text(value: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", value)).replace("\n", " ").strip()


def parse_optional_float(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)


def parse_market_number(value: str | int | float | None) -> float | None:
    if value in {None, "", "N/A"}:
        return None
    if isinstance(value, int | float):
        return float(value)
    cleaned = (
        value.replace("$", "")
        .replace(",", "")
        .replace("%", "")
        .strip()
    )
    if not cleaned:
        return None
    return float(cleaned)


def parse_date_timestamp(date_text: str) -> int:
    from datetime import datetime

    return int(datetime.strptime(date_text, "%Y-%m-%d").timestamp())


def parse_flexible_timestamp(value: str) -> int:
    from datetime import datetime

    value = value.strip()
    if value.isdigit():
        return int(value)
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return int(datetime.strptime(value, pattern).timestamp())
        except ValueError:
            pass
    raise ValueError(f"Unsupported date format: {value}")


def resolve_eastmoney_secid(instrument: Instrument) -> str:
    if instrument.eastmoney_secid:
        return instrument.eastmoney_secid
    symbol = instrument.symbol.strip()
    if not symbol.isdigit():
        raise RuntimeError("Instrument has no eastmoney_secid and symbol is not numeric.")
    if symbol.startswith(("5", "6", "9")):
        return f"1.{symbol}"
    if symbol.startswith(("0", "1", "2", "3")):
        return f"0.{symbol}"
    raise RuntimeError(f"Cannot infer Eastmoney secid for symbol {instrument.symbol}.")


def source_warning(symbol: str, source_name: str, exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"{symbol}/{source_name}: HTTP {exc.code} {exc.reason}"
    return f"{symbol}/{source_name}: {type(exc).__name__}: {exc}"


def source_enabled(source_config: dict[str, dict[str, Any]], source_name: str) -> bool:
    return bool(source_config.get(source_name, {}).get("enabled", False))


def safe_snapshot_name(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")
