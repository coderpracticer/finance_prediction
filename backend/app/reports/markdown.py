from __future__ import annotations

from datetime import UTC, datetime

from backend.app.models.schemas import ScreeningResponse


def render_markdown_report(
    screening: ScreeningResponse,
    llm_report: str,
    horizons: tuple[str, ...],
) -> str:
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    table_rows = "\n".join(
        "| {rank} | {symbol} | {score:.2f} | {confidence:.2f} | {quality} |".format(
            rank=candidate.rank,
            symbol=candidate.symbol,
            score=candidate.opportunity_score,
            confidence=candidate.confidence,
            quality=candidate.data_quality,
        )
        for candidate in screening.candidates
    )
    warnings = "\n".join(f"- {warning}" for warning in screening.warnings) or "- None"
    factor_sections = "\n\n".join(
        "\n".join(
            [
                f"### {candidate.rank}. {candidate.symbol} {candidate.name}",
                f"- Market: {candidate.market}",
                f"- Opportunity score: {candidate.opportunity_score:.2f}",
                f"- Confidence: {candidate.confidence:.2f}",
                f"- Data quality: {candidate.data_quality}",
                f"- Evidence summary: {candidate.thesis}",
                "",
                "| Group | Factor | Score | Confidence | Evidence |",
                "| --- | --- | ---: | ---: | --- |",
                *[
                    (
                        f"| {factor.group} | {factor.name} | {factor.score:.1f} | "
                        f"{factor.confidence:.2f} | {factor.evidence} |"
                    )
                    for factor in candidate.factors
                ],
            ]
        )
        for candidate in screening.candidates
    )
    return (
        "# Investment Research Report\n\n"
        f"- Generated at: {generated_at}\n"
        f"- Screening run: {screening.run_id}\n"
        f"- Horizons: {', '.join(horizons)}\n"
        f"- Candidate count: {len(screening.candidates)}\n\n"
        "## LLM Research Summary\n\n"
        f"{llm_report.strip()}\n\n"
        "## Ranked Candidates\n\n"
        "| Rank | Symbol | Opportunity Score | Confidence | Data Quality |\n"
        "| ---: | --- | ---: | ---: | --- |\n"
        f"{table_rows}\n\n"
        "## Structured Evidence\n\n"
        f"{factor_sections}\n\n"
        "## Data Source Warnings\n\n"
        f"{warnings}\n\n"
        "## Important Notice\n\n"
        "This report is generated from free public data and a local LLM for research triage only. "
        "It is not financial advice, a recommendation, or an automated trading signal.\n"
    )
