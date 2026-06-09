import json
import unittest

from backend.app.data_sources.spike import (
    parse_sec_companyfacts,
    parse_stooq_csv,
    parse_yahoo_chart,
    status_from,
)


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

    def test_status_from_classifies_results(self) -> None:
        self.assertEqual(status_from([], [], 10), "passed")
        self.assertEqual(status_from(["missing optional field"], [], 10), "partial")
        self.assertEqual(status_from([], [], 0), "weak")
        self.assertEqual(status_from([], ["HTTP 429"], 0), "failed")


if __name__ == "__main__":
    unittest.main()
