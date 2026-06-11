from __future__ import annotations

from backend.app.models.schemas import Candidate, ScreeningResponse


def build_report_prompt(screening: ScreeningResponse, horizons: tuple[str, ...]) -> str:
    horizon_text = ", ".join(horizons)
    candidates_text = "\n\n".join(format_candidate(candidate) for candidate in screening.candidates)
    warnings_text = "\n".join(f"- {warning}" for warning in screening.warnings) or "- None"
    return (
        "请基于以下免费公开数据源筛选结果，生成一份中文投资研究报告。\n"
        f"研究周期: {horizon_text}\n"
        f"运行 ID: {screening.run_id}\n\n"
        "输出要求:\n"
        "1. 使用 Markdown。\n"
        "2. 覆盖短线几天到几周、中期 1-3 个月两个视角。\n"
        "3. 先给总体结论和候选分层，再逐个分析 Top candidates。\n"
        "4. 每个候选至少包含 Why now、核心证据、主要风险、第一否定条件、后续验证动作。\n"
        "5. 明确说明这是研究优先级，不是确定性买卖建议。\n"
        "6. 不要使用未提供的实时价格、估值、财务数据或新闻细节。\n\n"
        "数据源警告:\n"
        f"{warnings_text}\n\n"
        "候选证据:\n"
        f"{candidates_text}"
    )


def format_candidate(candidate: Candidate) -> str:
    factors = "\n".join(
        f"- {factor.group}/{factor.name}: score={factor.score:.1f}, "
        f"confidence={factor.confidence:.2f}, evidence={factor.evidence}"
        for factor in candidate.factors
    )
    risks = "\n".join(f"- {risk}" for risk in candidate.risks)
    return (
        f"## Rank {candidate.rank}: {candidate.symbol} {candidate.name}\n"
        f"- Market: {candidate.market}\n"
        f"- Opportunity score: {candidate.opportunity_score:.2f}\n"
        f"- Confidence: {candidate.confidence:.2f}\n"
        f"- Data quality: {candidate.data_quality}\n"
        f"- Evidence summary: {candidate.thesis}\n"
        "Factors:\n"
        f"{factors}\n"
        "Known risks:\n"
        f"{risks}"
    )
