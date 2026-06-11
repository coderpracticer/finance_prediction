from __future__ import annotations

from datetime import UTC, datetime

from backend.app.config.settings import Settings
from backend.app.data_sources.connectors import DataSourceClient
from backend.app.factors.engine import aggregate_score, calculate_factors
from backend.app.models.schemas import Candidate, FactorScore, ScreeningResponse
from backend.app.storage.repository import ResearchRepository


class ScreeningService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.data_sources = DataSourceClient(settings.config_path, settings.raw_dir)
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
                        thesis=build_evidence_summary(factors),
                        risks=default_risks(data_quality, dataset.warnings),
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


def build_evidence_summary(factors: list[FactorScore]) -> str:
    top_factors = sorted(factors, key=lambda factor: factor.score, reverse=True)[:3]
    if not top_factors:
        return "No usable factor evidence was available."
    return "; ".join(
        f"{factor.group}/{factor.name} {factor.score:.1f}: {factor.evidence}"
        for factor in top_factors
    )


def default_risks(data_quality: str, warnings: list[str]) -> list[str]:
    risks = [
        "Free public data can be delayed, incomplete, rate-limited, or changed without notice.",
        "The screen is a research-priority tool and is not a buy/sell recommendation.",
    ]
    if data_quality != "good":
        risks.append("Current data quality is not strong enough for a high-conviction conclusion.")
    if warnings:
        risks.append("Some data sources produced warnings during this run.")
    return risks
