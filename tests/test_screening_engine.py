import unittest

from backend.app.factors.engine import aggregate_score, calculate_factors
from backend.app.models.schemas import (
    FundamentalSnapshot,
    Instrument,
    InstrumentDataset,
    NewsItem,
    PriceBar,
)
from backend.app.screening.service import build_evidence_summary, default_risks


class ScreeningEngineTests(unittest.TestCase):
    def test_calculate_factors_returns_core_groups(self) -> None:
        dataset = InstrumentDataset(
            instrument=Instrument(symbol="TEST", name="Test Corp"),
            prices=[
                PriceBar(timestamp=index, close=100 + index, volume=1000 + index * 10)
                for index in range(30)
            ],
            news=[NewsItem(title="Test catalyst") for _ in range(3)],
            fundamentals=FundamentalSnapshot(
                metric_count=3,
                available_metrics=["Revenues", "NetIncomeLoss", "EarningsPerShareDiluted"],
                has_revenue=True,
                has_net_income=True,
                has_eps=True,
            ),
        )

        factors = calculate_factors(dataset)
        groups = {factor.group for factor in factors}

        self.assertIn("Momentum", groups)
        self.assertIn("Volume/Attention", groups)
        self.assertIn("Event/Catalyst", groups)
        self.assertIn("Quality", groups)

    def test_aggregate_score_returns_data_quality(self) -> None:
        dataset = InstrumentDataset(
            instrument=Instrument(symbol="TEST", name="Test Corp"),
            prices=[
                PriceBar(timestamp=index, close=100 + index, volume=1000 + index * 10)
                for index in range(30)
            ],
            news=[NewsItem(title="Test catalyst")],
        )

        factors = calculate_factors(dataset)
        score, confidence, data_quality = aggregate_score(factors)

        self.assertGreater(score, 0)
        self.assertGreater(confidence, 0)
        self.assertIn(data_quality, {"good", "mixed", "weak"})

    def test_missing_price_history_marks_data_quality_weak(self) -> None:
        dataset = InstrumentDataset(
            instrument=Instrument(symbol="TEST", name="Test Corp"),
            prices=[],
            news=[NewsItem(title="Specific catalyst title") for _ in range(3)],
            fundamentals=FundamentalSnapshot(
                metric_count=3,
                available_metrics=["Revenues", "NetIncomeLoss", "EarningsPerShareDiluted"],
                has_revenue=True,
                has_net_income=True,
                has_eps=True,
            ),
        )

        factors = calculate_factors(dataset)
        _score, _confidence, data_quality = aggregate_score(factors)
        event_factor = next(factor for factor in factors if factor.name == "news_attention")

        self.assertEqual(data_quality, "weak")
        self.assertIn("Specific catalyst title", event_factor.evidence)

    def test_build_evidence_summary_uses_top_factors(self) -> None:
        dataset = InstrumentDataset(
            instrument=Instrument(symbol="TEST", name="Test Corp"),
            prices=[
                PriceBar(timestamp=index, close=100 + index, volume=1000 + index * 10)
                for index in range(30)
            ],
        )
        factors = calculate_factors(dataset)
        summary = build_evidence_summary(factors)

        self.assertIn("Momentum", summary)
        self.assertIn("return_20d", summary)

    def test_missing_china_etf_context_uses_neutral_evidence_text(self) -> None:
        dataset = InstrumentDataset(
            instrument=Instrument(symbol="510300", name="沪深300ETF"),
            prices=[
                PriceBar(timestamp=index, close=100 + index, volume=1000 + index * 10)
                for index in range(30)
            ],
        )

        evidence_text = "\n".join(factor.evidence for factor in calculate_factors(dataset))

        self.assertIn("当前未接入或未抓到可用的中文新闻", evidence_text)
        self.assertIn("当前未接入ETF规模", evidence_text)
        self.assertNotIn("Nasdaq RSS", evidence_text)
        self.assertNotIn("SEC companyfacts", evidence_text)

    def test_etf_product_metadata_becomes_quality_evidence(self) -> None:
        dataset = InstrumentDataset(
            instrument=Instrument(symbol="510300", name="沪深300ETF"),
            prices=[
                PriceBar(timestamp=index, close=100 + index, volume=1000 + index * 10)
                for index in range(30)
            ],
            fundamentals=FundamentalSnapshot(
                metric_count=3,
                available_metrics=["category", "tracking_index", "theme"],
                details={
                    "category": "宽基",
                    "tracking_index": "沪深300",
                    "theme": "A股核心资产",
                },
            ),
        )

        factors = calculate_factors(dataset)
        quality = next(factor for factor in factors if factor.name == "etf_product_profile")

        self.assertIn("跟踪指数=沪深300", quality.evidence)
        self.assertIn("主题=A股核心资产", quality.evidence)

    def test_default_risks_marks_weak_data_quality(self) -> None:
        risks = default_risks("weak", ["TEST/yahoo_chart_prices: HTTP 429"])

        self.assertTrue(any("数据质量" in risk for risk in risks))
        self.assertTrue(any("数据源警告" in risk for risk in risks))


if __name__ == "__main__":
    unittest.main()
