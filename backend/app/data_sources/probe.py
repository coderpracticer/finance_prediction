from __future__ import annotations

import argparse
import sys

from backend.app.config.settings import get_settings
from backend.app.data_sources.connectors import DataSourceClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe data sources for one symbol.")
    parser.add_argument("symbol", help="Ticker symbol, for example AAPL")
    args = parser.parse_args(argv)

    settings = get_settings()
    client = DataSourceClient(settings.config_path, settings.raw_dir)
    instruments = {instrument.symbol.upper(): instrument for instrument in client.universe()}
    symbol = args.symbol.upper()
    instrument = instruments.get(symbol)
    if instrument is None:
        print(f"{symbol}: not found in configured universe.")
        return 2

    sources = client.config["sources"]
    checks = [
        ("yahoo_chart_prices", lambda: client.fetch_yahoo_prices(instrument, sources["yahoo_chart_prices"])),
        ("stooq_prices", lambda: client.fetch_stooq_prices(instrument, sources["stooq_prices"])),
        ("nasdaq_stock_rss", lambda: client.fetch_nasdaq_news(instrument, sources["nasdaq_stock_rss"])),
    ]
    if instrument.cik:
        checks.append(
            (
                "sec_companyfacts",
                lambda: client.fetch_sec_companyfacts(instrument, sources["sec_companyfacts"]),
            )
        )

    failed = 0
    for source_name, check in checks:
        try:
            result = check()
            if isinstance(result, list):
                count = len(result)
            else:
                count = getattr(result, "metric_count", 1)
            print(f"PASS {symbol}/{source_name}: records={count}")
        except Exception as exc:  # noqa: BLE001 - diagnostic tool should report exact failures.
            failed += 1
            print(f"FAIL {symbol}/{source_name}: {type(exc).__name__}: {exc}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

