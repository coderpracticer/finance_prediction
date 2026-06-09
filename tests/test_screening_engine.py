import unittest

from backend.app.factors.engine import aggregate_score, calculate_factors
from backend.app.models.schemas import (
    FundamentalSnapshot,
    Instrument,
    InstrumentDataset,
    NewsItem,
    PriceBar,
)
from backend.app.research.local_llm import fallback_note


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

    def test_fallback_note_mentions_uncertainty(self) -> None:
        dataset = InstrumentDataset(
            instrument=Instrument(symbol="TEST", name="Test Corp"),
            prices=[PriceBar(timestamp=1, close=100, volume=1000)],
        )
        factors = calculate_factors(dataset)
        note = fallback_note(dataset, factors, 52.5, 0.42, "weak")

        self.assertIn("TEST", note)
        self.assertIn("机会", note)
        self.assertIn("数据质量", note)


if __name__ == "__main__":
    unittest.main()

