import json
import unittest

from backend.app.data_sources.spike import (
    parse_sec_companyfacts,
    parse_stooq_csv,
    parse_yahoo_chart,
    status_from,
)
from backend.app.data_sources.connectors import (
    build_cninfo_query_forms,
    parse_eastmoney_kline_prices,
    parse_cninfo_announcements,
    parse_date_timestamp,
    parse_local_price_csv,
    parse_nasdaq_historical_prices,
    parse_optional_float,
    parse_yahoo_price_bars,
    resolve_eastmoney_secid,
)
from backend.app.models.schemas import Instrument


class DataSourceSpikeTests(unittest.TestCase):
    def test_parse_stooq_csv_extracts_fields_and_rows(self) -> None:
        payload = (
            b"Date,Open,High,Low,Close,Volume\n"
            b"2026-06-08,100,105,99,104,123456\n"
        )

        fields, rows, warnings = parse_stooq_csv(payload)

        self.assertEqual(fields, ["Date", "Open", "High", "Low", "Close", "Volume"])
        self.assertEqual(rows, 1)
        self.assertEqual(warnings, [])

    def test_parse_sec_companyfacts_reports_common_metrics(self) -> None:
        payload = json.dumps(
            {
                "facts": {
                    "us-gaap": {
                        "Revenues": {"units": {"USD": []}},
                        "NetIncomeLoss": {"units": {"USD": []}},
                    }
                }
            }
        ).encode("utf-8")

        fields, records, warnings = parse_sec_companyfacts(payload)

        self.assertEqual(records, 2)
        self.assertIn("Revenues", fields)
        self.assertTrue(any("EarningsPerShareDiluted" in warning for warning in warnings))

    def test_parse_yahoo_chart_extracts_price_rows(self) -> None:
        payload = json.dumps(
            {
                "chart": {
                    "result": [
                        {
                            "timestamp": [1780790400],
                            "indicators": {
                                "quote": [
                                    {
                                        "open": [100.0],
                                        "high": [101.0],
                                        "low": [99.0],
                                        "close": [100.5],
                                        "volume": [1000],
                                    }
                                ]
                            },
                        }
                    ],
                    "error": None,
                }
            }
        ).encode("utf-8")

        fields, records, warnings = parse_yahoo_chart(payload)

        self.assertEqual(records, 1)
        self.assertIn("close", fields)
        self.assertEqual(warnings, [])

    def test_parse_yahoo_price_bars_returns_usable_prices(self) -> None:
        payload = json.dumps(
            {
                "chart": {
                    "result": [
                        {
                            "timestamp": [1780790400, 1780876800],
                            "indicators": {
                                "quote": [
                                    {
                                        "open": [100.0, 101.0],
                                        "high": [101.0, 103.0],
                                        "low": [99.0, 100.0],
                                        "close": [100.5, 102.0],
                                        "volume": [1000, 1200],
                                    }
                                ]
                            },
                        }
                    ],
                    "error": None,
                }
            }
        ).encode("utf-8")

        prices = parse_yahoo_price_bars(payload)

        self.assertEqual(len(prices), 2)
        self.assertEqual(prices[-1].close, 102.0)
        self.assertEqual(prices[-1].volume, 1200)

    def test_parse_local_price_csv_accepts_ohlcv_file(self) -> None:
        text = (
            "Date,Open,High,Low,Close,Volume\n"
            "2026-06-10,100,103,99,102,1000\n"
            "2026-06-11,102,105,101,104,1200\n"
        )

        prices = parse_local_price_csv(text)

        self.assertEqual(len(prices), 2)
        self.assertEqual(prices[0].close, 102)
        self.assertEqual(prices[-1].volume, 1200)

    def test_parse_nasdaq_historical_prices_returns_usable_prices(self) -> None:
        payload = json.dumps(
            {
                "data": {
                    "tradesTable": {
                        "rows": [
                            {
                                "date": "06/10/2026",
                                "close": "$102.00",
                                "volume": "1,000",
                                "open": "$100.00",
                                "high": "$103.00",
                                "low": "$99.00",
                            },
                            {
                                "date": "06/11/2026",
                                "close": "$104.00",
                                "volume": "1,200",
                                "open": "$102.00",
                                "high": "$105.00",
                                "low": "$101.00",
                            },
                        ]
                    }
                }
            }
        ).encode("utf-8")

        prices = parse_nasdaq_historical_prices(payload)

        self.assertEqual(len(prices), 2)
        self.assertEqual(prices[-1].close, 104)
        self.assertEqual(prices[-1].volume, 1200)

    def test_parse_eastmoney_kline_prices_returns_usable_prices(self) -> None:
        payload = json.dumps(
            {
                "data": {
                    "klines": [
                        "2026-06-10,3.000,3.100,3.120,2.980,100000,310000000,4.1,2.0,0.06,1.2",
                        "2026-06-11,3.100,3.200,3.240,3.080,120000,384000000,5.0,3.2,0.10,1.4",
                    ]
                }
            }
        ).encode("utf-8")

        prices = parse_eastmoney_kline_prices(payload)

        self.assertEqual(len(prices), 2)
        self.assertEqual(prices[-1].close, 3.2)
        self.assertEqual(prices[-1].volume, 120000)

    def test_parse_cninfo_announcements_returns_news_items(self) -> None:
        payload = json.dumps(
            {
                "announcements": [
                    {
                        "announcementTitle": "沪深300ETF<em>基金</em>份额变动公告",
                        "adjunctUrl": "finalpage/2026-06-12/test.PDF",
                        "announcementTime": 1781193600000,
                    }
                ]
            }
        ).encode("utf-8")

        items = parse_cninfo_announcements(payload)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "沪深300ETF基金份额变动公告")
        self.assertEqual(items[0].source, "巨潮资讯")
        self.assertEqual(items[0].category, "announcement")
        self.assertIn("static.cninfo.com.cn", items[0].link or "")

    def test_build_cninfo_query_forms_includes_fund_search_fallbacks(self) -> None:
        forms = build_cninfo_query_forms(
            Instrument(
                symbol="510300",
                name="沪深300ETF",
                exchange="SH",
                tracking_index="沪深300",
            ),
            page_size=5,
        )

        self.assertGreaterEqual(len(forms), 4)
        self.assertEqual(forms[0]["stock"], "510300")
        self.assertTrue(any(form["searchkey"] == "沪深300ETF" for form in forms))
        self.assertTrue(any(form["column"] == "fund" for form in forms))

    def test_resolve_eastmoney_secid_handles_cn_etfs(self) -> None:
        self.assertEqual(
            resolve_eastmoney_secid(Instrument(symbol="510300", name="沪深300ETF")),
            "1.510300",
        )
        self.assertEqual(
            resolve_eastmoney_secid(Instrument(symbol="159915", name="创业板ETF")),
            "0.159915",
        )

    def test_status_from_classifies_results(self) -> None:
        self.assertEqual(status_from([], [], 10), "passed")
        self.assertEqual(status_from(["missing optional field"], [], 10), "partial")
        self.assertEqual(status_from([], [], 0), "weak")
        self.assertEqual(status_from([], ["HTTP 429"], 0), "failed")

    def test_price_parser_helpers(self) -> None:
        self.assertEqual(parse_optional_float("123.45"), 123.45)
        self.assertIsNone(parse_optional_float(""))
        self.assertGreater(parse_date_timestamp("2026-06-09"), 0)


if __name__ == "__main__":
    unittest.main()
