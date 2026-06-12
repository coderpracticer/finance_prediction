from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable

from backend.app.config.settings import Settings
from backend.app.data_sources.connectors import DataSourceClient
from backend.app.factors.engine import aggregate_score, calculate_factors
from backend.app.models.schemas import Candidate, FactorScore, ScreeningResponse
from backend.app.storage.repository import ResearchRepository


class ScreeningService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.data_sources = DataSourceClient(
            settings.config_path,
            settings.raw_dir,
            price_csv_dir=settings.price_csv_dir,
        )
        self.repository = ResearchRepository(settings.database_path)

    def run(
        self,
        limit: int = 10,
        progress: Callable[[str], None] | None = None,
    ) -> ScreeningResponse:
        candidates: list[Candidate] = []
        warnings: list[str] = []
        sufficient_price_count = 0
        report_progress = progress or (lambda _message: None)
        universe = self.data_sources.universe()
        universe_sample = ", ".join(
            f"{instrument.symbol}:{instrument.market}" for instrument in universe[:5]
        )
        report_progress(
            f"loaded universe; instruments={len(universe)}; sample=[{universe_sample}]"
        )
        for index, instrument in enumerate(universe, start=1):
            report_progress(f"[{index}/{len(universe)}] fetching {instrument.symbol}")
            try:
                dataset = self.data_sources.fetch_dataset(instrument, progress=report_progress)
                if len(dataset.prices) >= self.settings.min_price_rows:
                    sufficient_price_count += 1
                warnings.extend(dataset.warnings)
                report_progress(
                    f"[{index}/{len(universe)}] calculating factors for {instrument.symbol}; "
                    f"prices={len(dataset.prices)}, news={len(dataset.news)}, "
                    f"warnings={len(dataset.warnings)}"
                )
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
                report_progress(
                    f"[{index}/{len(universe)}] {instrument.symbol} score={score:.2f}, "
                    f"confidence={confidence:.2f}, quality={data_quality}"
                )
            except Exception as exc:  # noqa: BLE001 - source-specific failures should not kill run.
                warnings.append(f"{instrument.symbol}: {type(exc).__name__}: {exc}")
                report_progress(
                    f"[{index}/{len(universe)}] {instrument.symbol} failed: "
                    f"{type(exc).__name__}: {exc}"
                )

        self._enforce_price_coverage(
            sufficient_price_count=sufficient_price_count,
            universe_count=len(universe),
        )

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

    def _enforce_price_coverage(self, sufficient_price_count: int, universe_count: int) -> None:
        if not self.settings.require_price_history:
            return
        if universe_count <= 0:
            return
        coverage_ratio = sufficient_price_count / universe_count
        if coverage_ratio < self.settings.min_price_coverage_ratio:
            required = self.settings.min_price_coverage_ratio * 100
            actual = coverage_ratio * 100
            raise RuntimeError(
                "Price history coverage gate failed: "
                f"{sufficient_price_count}/{universe_count} instruments have at least "
                f"{self.settings.min_price_rows} price rows "
                f"({actual:.1f}% < required {required:.1f}%). "
                "Fix price data sources, set FRA_PRICE_CSV_DIR, or rerun with "
                "--allow-weak-price-data for diagnostics only."
            )


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
        "免费公开数据可能存在延迟、缺失、限流或接口变更。",
        "当前筛选结果只是研究参考，不是确定性买卖建议。",
    ]
    if data_quality != "good":
        risks.append("当前数据质量不足以支撑高置信度结论。")
    if warnings:
        risks.append("本次运行存在数据源警告，需要降低结论强度。")
    return risks
