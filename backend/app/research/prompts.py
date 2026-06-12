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
        "审计行情、新闻、公告、宏观和跨资产数据的覆盖率、时效性、异常值、缓存使用、来源冲突和可用性边界。",
        "只评价数据是否足以支撑结论，不给买卖建议；必须指出哪些结论不能被当前数据支持。",
    ),
    (
        "macro_cross_asset_strategist",
        "宏观与跨资产策略智能体",
        "分析利率、汇率、商品、债券、权益、Crypto 和风险偏好之间的联动，判断市场环境对不同资产的影响。",
        "只基于已提供的宏观和跨资产证据；没有宏观数据时必须说明无法形成宏观判断。",
    ),
    (
        "a_share_equity_analyst",
        "A股权益分析智能体",
        "分析 A股个股和行业的业绩、估值、公告、政策催化、行业景气和资金关注度。",
        "只分析系统传入的 A股标的和证据；不得补充未提供的财务或公告内容。",
    ),
    (
        "china_etf_style_rotation_analyst",
        "中国 ETF 风格轮动智能体",
        "比较宽基、红利、行业主题、商品、跨境 ETF 的相对强弱、拥挤度、轮动线索和再平衡机会。",
        "只讨论中国上市 ETF；跨境 ETF 作为中国上市交易品种分析，不做海外个股预测。",
    ),
    (
        "fixed_income_fx_analyst",
        "债券与外汇分析智能体",
        "分析债券收益率、信用风险、人民币汇率、美元指数和主要外汇对权益、商品和 ETF 的影响。",
        "没有利率、汇率或债券数据时，不得推断债券和外汇结论。",
    ),
    (
        "commodity_analyst",
        "商品市场分析智能体",
        "分析黄金、原油、有色、黑色、农产品等商品价格趋势、供需线索、通胀预期和避险属性。",
        "只使用已提供的商品行情、新闻和宏观证据；不得编造库存、产量或地缘事件。",
    ),
    (
        "crypto_market_analyst",
        "Crypto 市场分析智能体",
        "分析 BTC、ETH 和主流 Crypto 的趋势、波动、资金情绪、风险偏好和与传统资产的联动。",
        "Crypto 属于高波动高风险资产；没有交易所、链上或资金数据时必须降低结论强度。",
    ),
    (
        "momentum_technical_analyst",
        "动量与技术面智能体",
        "分析 5/20/60 日收益、均线偏离、波动、回撤、成交量变化、趋势强度和关键失效位置。",
        "只使用结构化因子证据；价格数据不足时必须说明无法形成技术判断。",
    ),
    (
        "news_announcement_fundamental_analyst",
        "新闻公告与产品资料智能体",
        "分析中文新闻、交易所/巨潮公告、ETF产品资料、跟踪指数、主题定位和风险画像，判断非价格证据是否支持投资结论。",
        "必须区分已经抓取到的公告/产品资料和仍然缺失的数据；不能把没有抓到新闻解读为没有风险。",
    ),
    (
        "news_event_analyst",
        "新闻事件分析智能体",
        "分析新闻、公告、政策、财报、行业事件和突发催化，判断事件是否可能改变预期。",
        "不能把新闻数量当成充分理由；必须评估新闻新颖度、相关性、时效性和是否已被价格反映。",
    ),
    (
        "risk_challenger",
        "风险反证智能体",
        "寻找回撤、波动、估值、政策、流动性、拥挤交易、数据缺口、过度解读和第一否定条件。",
        "必须优先挑战正向结论；不写正向推荐，不迎合最终结论。",
    ),
    (
        "portfolio_sizing_advisor",
        "组合仓位建议智能体",
        "根据机会强度、置信度、波动、回撤、资产相关性和普通投资者适用性，给出审慎仓位区间。",
        "只给区间和情景化建议，不给绝对交易指令；高风险资产必须设置更低仓位上限。",
    ),
    (
        "compliance_guardian",
        "合规与表达审查智能体",
        "审查报告是否存在收益承诺、确定性表述、个性化投顾暗示、忽视风险或证据不足的问题。",
        "只做合规和表达审查，不改变投资逻辑；必须要求最终报告包含免责声明。",
    ),
    (
        "opportunity_scout",
        "机会侦察智能体",
        "识别值得进入研究池、观察池或回避池的标的，提出 Why now、潜在催化和验证动作。",
        "只给研究优先级和审慎建议，不得把低置信度线索包装成确定性机会。",
    ),
)


GLOBAL_INVESTMENT_CONSTRAINTS = (
    "硬性约束："
    "只能使用用户提供或系统抓取并传入的证据，不得编造实时价格、新闻、财务、公告、政策或链上数据。"
    "如果数据缺失、过旧、来源不稳定或互相冲突，必须明确降低结论强度。"
    "可以给出审慎投资建议、评级、仓位区间、观察条件和风险控制，但不得承诺收益，"
    "不得给出确定性判断。必须区分事实、推断、假设和建议。"
    "必须说明关键风险、第一失效条件和需要继续验证的数据。"
    "输出面向普通投资者，语言清晰、克制、可执行。"
    "不输出 <think>、内部推理草稿或链式思考过程。"
    "本内容不构成个性化投资建议，不替代持牌投资顾问服务。"
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
        "请基于以下免费公开数据源筛选结果，生成一份中文专业投资团队研究报告。\n"
        "研究范围以系统传入的标的和证据为准；当前默认数据主要覆盖 A股和中国上市 ETF。"
        "数据源扩展后可覆盖 ETF、债券、商品、外汇、Crypto 等可抓取资产。\n"
        f"研究周期: {horizon_text}\n"
        f"运行 ID: {screening.run_id}\n\n"
        "当前系统采用以下专业投资团队分工，并由投资委员会式最终综合流程汇总：\n"
        f"{agent_role_text}\n\n"
        "输出要求:\n"
        "1. 使用 Markdown。\n"
        "2. 报告必须比候选列表更深入，不能只重复分数；正文要面向新手投资者解释“为什么”和“怎么看”。\n"
        "3. 先写“总体结论”，说明本次筛选是否适合继续研究、数据质量如何、主要约束是什么。\n"
        "4. 给出“投资委员会评级”和“候选分层”：优先配置、小仓观察、持有观察、减配回避、数据不足。\n"
        "5. 逐个分析 Top candidates。每个候选必须包含：Why now、短线几天到几周观点、"
        "中期1-3个月观点、核心证据、评级建议、建议动作、仓位区间、主要风险、第一失效条件、后续验证动作。\n"
        "6. 优先使用 Momentum、Risk、Volume/Attention、Event/Catalyst、Quality、"
        "Data Coverage 等结构化因子作为证据。\n"
        "7. 如果价格、成交量或基本面数据缺失，必须明确降低结论强度，不能用主观判断补齐。\n"
        "8. 中国 ETF 报告应强调相对强弱、风格切换、回撤风险、成交活跃度和可验证的跟踪动作。\n"
        "9. 不要输出 <think>、推理草稿、内部分析过程，只输出最终报告。\n"
        "10. 明确说明这是普通投资者研究参考，不是收益承诺、个性化投资建议或交易指令。\n"
        "11. 不要使用未提供的实时价格、估值、财务数据或新闻细节。\n"
        "12. 必须包含免责声明：本报告基于公开信息和系统抓取数据自动生成，仅供一般性研究参考，"
        "不构成个性化投资建议、收益承诺或交易指令。投资者应结合自身风险承受能力、投资期限和财务状况独立决策，"
        "必要时咨询持牌专业人士。\n"
        "13. 每个重点标的至少写 6-8 个具体要点，说明适合哪类投资者、不适合哪类投资者、买前要观察什么、"
        "什么时候应该放弃该观点。\n"
        "14. 首次出现“波动率、最大回撤、均线、成交量放大、置信度、仓位区间”等术语时，"
        "必须用一句通俗语言解释其投资含义。\n"
        "15. 必须给出明确但审慎的投资建议，不能只写“继续观察”。建议动作只能使用："
        "优先配置、小仓试探、持有观察、减仓、回避、数据不足暂不参与；同时给出原因和触发条件。\n\n"
        "16. 必须解释 ETF 是交易型开放式指数基金，说明该 ETF 跟踪什么、相当于买入哪类资产、"
        "为什么它不同于单只股票。\n"
        "17. 失效条件必须分成四类：趋势失效、风险失效、事件/公告失效、数据失效。"
        "不要对所有标的套用同一句机械规则。\n\n"
        "建议结构:\n"
        "## 新手先看\n"
        "## 总体结论\n"
        "## ETF入门说明\n"
        "## 投资委员会评级\n"
        "## 候选分层\n"
        "## 重点标的分析\n"
        "## 建议动作与仓位区间\n"
        "## 主要风险与第一失效条件\n"
        "## 数据质量与限制\n"
        "## 术语解释\n"
        "## 后续观察清单\n"
        "## 免责声明\n\n"
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
                    "研究范围以系统传入的标的和证据为准，当前默认主要覆盖 A股和中国上市 ETF。"
                    f"{GLOBAL_INVESTMENT_CONSTRAINTS}"
                    "输出要简洁但具体，服务于最终中文专业投资团队报告。"
                ),
                user_prompt=(
                    f"研究周期: {horizon_text}\n\n"
                    "请完成你的专业投资团队角色任务。\n"
                    "输出格式:\n"
                    "1. 角色结论\n"
                    "2. 支持证据\n"
                    "3. 反向证据或不确定性\n"
                    "4. 评级建议\n"
                    "5. 置信度：高 / 中 / 低\n"
                    "6. 给新手投资者的解释\n"
                    "7. 对最终报告的建议\n"
                    "8. 不应被最终报告采纳的过度解读\n\n"
                    "评级建议只能使用:\n"
                    "- 积极关注\n"
                    "- 谨慎增配\n"
                    "- 持有观察\n"
                    "- 减配\n"
                    "- 回避\n"
                    "- 数据不足，暂不评级\n\n"
                    "约束:\n"
                    "- 只能基于下方证据。\n"
                    "- 不得编造未提供的数据。\n"
                    "- 数据不足时必须降低结论强度。\n"
                    "- 不输出 <think>、推理草稿或内部分析过程。\n\n"
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
        "请作为投资委员会主席、风险复核人、合规审查人和最终研究写作智能体，"
        "基于候选证据和各专业智能体中间结论完成多轮综合。\n\n"
        "你需要在内部完成以下步骤，但最终只输出报告正文：\n"
        "1. 识别各智能体之间的一致结论和重大分歧。\n"
        "2. 对正向结论进行反证检查。\n"
        "3. 对证据不足的观点降级或删除。\n"
        "4. 形成投资委员会评级、建议动作和仓位区间。\n"
        "5. 审查是否存在收益承诺、确定性买卖指令或个性化投顾暗示。\n"
        "6. 生成面向普通投资者的中文投资报告。\n"
        "7. 给出明确但审慎的投资建议，避免只写模糊观察。每个重点标的必须落到"
        "优先配置、小仓试探、持有观察、减仓、回避或数据不足暂不参与之一。\n\n"
        "8. 对每个重点标的设置四类失效条件：趋势失效、风险失效、事件/公告失效、数据失效。"
        "不要使用对所有标的都一样的机械止损句。\n\n"
        "最终报告必须包含：\n"
        "## 新手先看\n"
        "## 总体结论\n"
        "## ETF入门说明\n"
        "## 投资委员会评级\n"
        "## 候选分层\n"
        "## 重点标的分析\n"
        "## 建议动作与仓位区间\n"
        "## 主要风险与第一失效条件\n"
        "## 数据质量与限制\n"
        "## 术语解释\n"
        "## 后续观察清单\n"
        "## 免责声明\n\n"
        "仓位区间必须审慎：\n"
        "- 高置信度低波动标的：5%-15%\n"
        "- 中等置信度标的：3%-8%\n"
        "- 高波动或数据不足标的：0%-3%\n"
        "- Crypto 等高风险资产：普通投资者原则上不超过 0%-5%\n\n"
        "免责声明必须包含：本报告基于公开信息和系统抓取数据自动生成，仅供一般性研究参考，"
        "不构成个性化投资建议、收益承诺或交易指令。投资者应结合自身风险承受能力、投资期限和财务状况独立决策，"
        "必要时咨询持牌专业人士。\n\n"
        "写作深度要求：报告必须适合新手阅读，不能只给结论。每个重点 ETF 需要解释："
        "它是什么、近期发生了什么、这些指标为什么重要、可能赚什么钱、可能亏在哪里、"
        "买前观察什么、什么情况下应该停止跟踪或降低仓位。"
        "投资建议必须放在每个标的分析的醒目位置，包含建议动作、适合投资者、仓位区间、买入前提和退出条件。\n\n"
        "投资建议规则：每个标的必须给出明确动作，但要审慎表达。"
        "失效条件必须围绕该标的自身特点写成四类："
        "趋势失效，例如跌破关键均线且成交量没有修复；"
        "风险失效，例如回撤或波动明显超过可承受范围；"
        "事件/公告失效，例如政策、公告或行业数据与原假设相反；"
        "数据失效，例如关键数据缺失、公告源不可用或产品资料过旧。\n\n"
        "必须保留分歧和数据限制，不能为了形成结论而忽略风险。"
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
