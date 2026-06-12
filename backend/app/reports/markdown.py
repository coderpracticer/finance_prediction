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
    warning_summary = summarize_warnings(screening.warnings)
    factor_sections = "\n\n".join(
        "\n".join(
            [
                f"### {candidate.rank}. {candidate.symbol} {candidate.name}",
                f"- Market: {candidate.market}",
                f"- Opportunity score: {candidate.opportunity_score:.2f}",
                f"- Confidence: {candidate.confidence:.2f}",
                f"- Data quality: {candidate.data_quality}",
                f"- Evidence summary: {candidate.thesis}",
                f"- Risks: {'; '.join(candidate.risks)}",
                "",
                "| Group | Factor | Score | Confidence | Raw Value | Evidence |",
                "| --- | --- | ---: | ---: | ---: | --- |",
                *[
                    (
                        f"| {factor.group} | {factor.name} | {factor.score:.1f} | "
                        f"{factor.confidence:.2f} | {factor.raw_value if factor.raw_value is not None else '-'} | "
                        f"{factor.evidence} |"
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
        "## Data Source Health\n\n"
        f"{warning_summary}\n\n"
        "## LLM Research Summary\n\n"
        f"{strip_reasoning_blocks(llm_report).strip()}\n\n"
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


def summarize_warnings(warnings: list[str]) -> str:
    if not warnings:
        return "- No data source warnings."
    source_counts: dict[str, int] = {}
    cache_count = 0
    for warning in warnings:
        if "_cache:" in warning:
            cache_count += 1
        parts = warning.split(":", 1)[0].split("/", 1)
        source = parts[1] if len(parts) > 1 else "unknown"
        source_counts[source] = source_counts.get(source, 0) + 1
    lines = [
        f"- Total warnings: {len(warnings)}",
        f"- Cached fallbacks used: {cache_count}",
    ]
    for source, count in sorted(source_counts.items()):
        lines.append(f"- {source}: {count}")
    return "\n".join(lines)


def strip_reasoning_blocks(content: str) -> str:
    while True:
        start = content.find("<think>")
        end = content.find("</think>")
        if start == -1 or end == -1 or end < start:
            return content
        content = content[:start] + content[end + len("</think>") :]
