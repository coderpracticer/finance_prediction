from __future__ import annotations

from dataclasses import dataclass

from backend.app.models.schemas import Candidate, ScreeningResponse


@dataclass(frozen=True)
class AgentPrompt:
    name: str
    system_prompt: str
    user_prompt: str


AGENT_ROLES: tuple[tuple[str, str, str, str], ...] = (
    (
        "data_quality_auditor",
        "数据质量审计智能体",
        "审计数据覆盖、缓存使用、数据源警告和结论可信度边界。",
        "只评价数据是否足以支撑研究；不要讨论买卖机会。",
    ),
    (
        "momentum_technical_analyst",
        "动量与技术面智能体",
        "分析多周期收益、均线偏离、成交量变化和短中期价格趋势。",
        "只使用 Momentum、Risk、Volume/Attention 和 Data Coverage 因子；价格不足时必须说无法形成技术判断。",
    ),
    (
        "risk_challenger",
        "风险反证智能体",
        "优先寻找回撤、波动、数据缺口、过度解读和第一否定条件。",
        "必须给出每类候选的第一否定条件；不要写正向推荐。",
    ),
    (
        "opportunity_scout",
        "机会发现智能体",
        "基于结构化证据识别值得继续研究的候选、Why now 和后续验证动作。",
        "只提出研究优先级和验证动作；不得把新闻数量当作充分投资理由。",
    ),
)


def build_report_prompt(screening: ScreeningResponse, horizons: tuple[str, ...]) -> str:
    agent_role_text = "\n".join(
        f"- {display_name}: {responsibility} 角色边界：{boundary}"
        for _role_id, display_name, responsibility, boundary in AGENT_ROLES
    )
    horizon_text = ", ".join(horizons)
    candidates_text = "\n\n".join(format_candidate(candidate) for candidate in screening.candidates)
    warnings_text = "\n".join(f"- {warning}" for warning in screening.warnings) or "- None"
    return (
        "请基于以下免费公开数据源筛选结果，生成一份中文投资研究报告。\n"
        f"研究周期: {horizon_text}\n"
        f"运行 ID: {screening.run_id}\n\n"
        "当前系统建议采用以下轻量智能体分工，并由最终研究写作智能体综合：\n"
        f"{agent_role_text}\n\n"
        "输出要求:\n"
        "1. 使用 Markdown。\n"
        "2. 报告必须比候选列表更深入，不能只是重复分数。\n"
        "3. 先写一段「总体结论」，说明本次筛选是否适合继续研究、数据质量如何、主要约束是什么。\n"
        "4. 给出「候选分层」：优先研究、观察、暂缓，并解释分层依据。\n"
        "5. 逐个分析 Top candidates。每个候选必须包含：Why now、短线几天到几周观点、"
        "中期 1-3 个月观点、核心证据、主要风险、第一否定条件、后续验证动作。\n"
        "6. 优先使用 Momentum、Risk、Volume/Attention、Event/Catalyst、Quality、Data Coverage "
        "这些结构化因子作为证据。\n"
        "7. 如果价格、成交量或基本面数据缺失，必须明确降低结论强度，不要把新闻数量当成充分买入理由。\n"
        "8. 只能基于新闻标题样例描述事件主题；如果只看到新闻数量而没有标题，不得推断新闻主题。\n"
        "9. 不要输出 <think>、推理草稿、内部分析过程，只输出最终报告。\n"
        "10. 明确说明这是研究优先级，不是确定性买卖建议。\n"
        "11. 不要使用未提供的实时价格、估值、财务数据或新闻细节。\n\n"
        "建议结构:\n"
        "## 总体结论\n"
        "## 候选分层\n"
        "## Top Candidates 深度分析\n"
        "## 共性风险与数据缺口\n"
        "## 下一步验证清单\n\n"
        "数据源警告:\n"
        f"{warnings_text}\n\n"
        "候选证据:\n"
        f"{candidates_text}"
    )


def build_agent_prompts(
    screening: ScreeningResponse,
    horizons: tuple[str, ...],
) -> list[AgentPrompt]:
    horizon_text = ", ".join(horizons)
    evidence = build_evidence_block(screening)
    prompts: list[AgentPrompt] = []
    for role_id, display_name, responsibility, boundary in AGENT_ROLES:
        prompts.append(
            AgentPrompt(
                name=role_id,
                system_prompt=(
                    f"你是{display_name}。{responsibility}"
                    f"角色边界：{boundary}"
                    "只能基于用户提供的结构化证据分析，不得编造未提供的数据。"
                    "不要输出 <think>、推理草稿或内部分析过程。"
                    "输出要简洁但具体，服务于最终中文投资研究报告。"
                ),
                user_prompt=(
                    f"研究周期: {horizon_text}\n\n"
                    "请完成你的智能体分析任务。\n"
                    "输出格式:\n"
                    "1. 关键观察\n"
                    "2. 支持证据\n"
                    "3. 主要风险或限制\n"
                    "4. 对最终报告的建议\n"
                    "5. 不应被最终报告采用的过度解读\n\n"
                    f"{evidence}"
                ),
            )
        )
    return prompts


def build_synthesis_prompt(
    screening: ScreeningResponse,
    horizons: tuple[str, ...],
    agent_outputs: dict[str, str],
) -> str:
    agent_sections = "\n\n".join(
        f"## {name}\n{content.strip()}" for name, content in agent_outputs.items()
    )
    return (
        f"{build_report_prompt(screening, horizons)}\n\n"
        "多智能体中间结论:\n"
        f"{agent_sections}\n\n"
        "请作为最终研究写作智能体，综合候选证据和各智能体中间结论，"
        "生成完整中文研究报告。需要保留分歧和数据限制，不能为了形成结论而忽略风险。"
        "不要输出 <think>、推理草稿或内部分析过程。"
    )


def build_evidence_block(screening: ScreeningResponse) -> str:
    candidates_text = "\n\n".join(format_candidate(candidate) for candidate in screening.candidates)
    warnings_text = "\n".join(f"- {warning}" for warning in screening.warnings) or "- None"
    return (
        "数据源警告:\n"
        f"{warnings_text}\n\n"
        "候选证据:\n"
        f"{candidates_text}"
    )


def format_candidate(candidate: Candidate) -> str:
    factors = "\n".join(
        f"- {factor.group}/{factor.name}: score={factor.score:.1f}, "
        f"confidence={factor.confidence:.2f}, raw_value={factor.raw_value}, "
        f"evidence={factor.evidence}"
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
