from __future__ import annotations

from datetime import UTC, datetime

from backend.app.config.settings import Settings
from backend.app.data_sources.connectors import DataSourceClient
from backend.app.factors.engine import aggregate_score, calculate_factors
from backend.app.models.schemas import Candidate, ScreeningResponse
from backend.app.research.local_llm import LocalLLMResearchWriter
from backend.app.storage.repository import ResearchRepository


class ScreeningService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.data_sources = DataSourceClient(settings.config_path, settings.raw_dir)
        self.writer = LocalLLMResearchWriter(settings)
        self.repository = ResearchRepository(settings.database_path)

    def run(self, limit: int = 10) -> ScreeningResponse:
        candidates: list[Candidate] = []
        warnings: list[str] = []
        for instrument in self.data_sources.universe():
            try:
                dataset = self.data_sources.fetch_dataset(instrument)
                warnings.extend(dataset.warnings)
                factors = calculate_factors(dataset)
                score, confidence, data_quality = aggregate_score(factors)
                thesis, risks = self.writer.write_candidate_note(
                    dataset,
                    factors,
                    score,
                    confidence,
                    data_quality,
                )
                candidates.append(
                    Candidate(
                        symbol=instrument.symbol,
                        name=instrument.name,
                        market=instrument.market,
                        rank=0,
                        opportunity_score=score,
                        confidence=confidence,
                        data_quality=data_quality,
                        factors=factors,
                        thesis=thesis,
                        risks=risks,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - source-specific failures should not kill run.
                warnings.append(f"{instrument.symbol}: {type(exc).__name__}: {exc}")

        candidates.sort(key=lambda candidate: candidate.opportunity_score, reverse=True)
        for index, candidate in enumerate(candidates[:limit], start=1):
            candidate.rank = index

        response = ScreeningResponse(
            run_id=datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"),
            status="success" if candidates else "failed",
            candidates=candidates[:limit],
            warnings=warnings,
        )
        self.repository.save_screening_response(response)
        return response

    def latest(self) -> ScreeningResponse | None:
        return self.repository.get_latest_screening_response()
