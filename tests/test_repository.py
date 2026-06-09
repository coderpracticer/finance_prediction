import tempfile
import unittest
from pathlib import Path

from backend.app.models.schemas import Candidate, FactorScore, ScreeningResponse
from backend.app.storage.repository import ResearchRepository


class ResearchRepositoryTests(unittest.TestCase):
    def test_save_and_load_latest_screening_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ResearchRepository(Path(temp_dir) / "app.db")
            response = ScreeningResponse(
                run_id="run-1",
                status="success",
                candidates=[
                    Candidate(
                        symbol="AAPL",
                        name="Apple Inc.",
                        market="US",
                        rank=1,
                        opportunity_score=75.5,
                        confidence=0.8,
                        data_quality="good",
                        factors=[
                            FactorScore(
                                name="price_momentum",
                                group="Momentum",
                                score=82.0,
                                confidence=0.9,
                                evidence="Close improved over lookback.",
                            )
                        ],
                        thesis="AAPL is an opportunity candidate.",
                        risks=["Data can be stale."],
                    )
                ],
            )

            repository.save_screening_response(response)
            loaded = repository.get_latest_screening_response()

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.run_id, "run-1")
            self.assertEqual(loaded.candidates[0].symbol, "AAPL")
            self.assertEqual(loaded.candidates[0].factors[0].group, "Momentum")

    def test_get_candidate_by_symbol_uses_latest_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ResearchRepository(Path(temp_dir) / "app.db")
            for run_id, score in [("run-1", 50.0), ("run-2", 80.0)]:
                repository.save_screening_response(
                    ScreeningResponse(
                        run_id=run_id,
                        status="success",
                        candidates=[
                            Candidate(
                                symbol="MSFT",
                                name="Microsoft Corporation",
                                market="US",
                                rank=1,
                                opportunity_score=score,
                                confidence=0.7,
                                data_quality="good",
                                factors=[],
                                thesis=f"Score {score}",
                                risks=[],
                            )
                        ],
                    )
                )

            candidate = repository.get_candidate_by_symbol("msft")

            self.assertIsNotNone(candidate)
            self.assertEqual(candidate.opportunity_score, 80.0)


if __name__ == "__main__":
    unittest.main()

