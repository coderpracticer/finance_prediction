from __future__ import annotations

from datetime import UTC, datetime

from backend.app.models.schemas import ScreeningResponse


FACTOR_GROUP_LABELS = {
    "Data Coverage": "数据覆盖",
    "Momentum": "趋势动量",
    "Risk": "风险波动",
    "Volume/Attention": "成交关注度",
    "Event/Catalyst": "事件催化",
    "Quality": "产品资料",
}

DATA_QUALITY_LABELS = {
    "good": "较好",
    "mixed": "一般",
    "weak": "较弱",
}


def render_markdown_report(
    screening: ScreeningResponse,
    llm_report: str,
    horizons: tuple[str, ...],
) -> str:
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    table_rows = "\n".join(
        "| {rank} | {symbol} | {name} | {score:.2f} | {confidence:.2f} | {quality} |".format(
            rank=candidate.rank,
            symbol=candidate.symbol,
            name=candidate.name,
            score=candidate.opportunity_score,
            confidence=candidate.confidence,
            quality=DATA_QUALITY_LABELS.get(candidate.data_quality, candidate.data_quality),
        )
        for candidate in screening.candidates
    )
    warnings = "\n".join(f"- {warning}" for warning in screening.warnings) or "- 无"
    warning_summary = summarize_warnings(screening.warnings)
    factor_sections = "\n\n".join(
        "\n".join(
            [
                f"### {candidate.rank}. {candidate.symbol} {candidate.name}",
                f"- 市场：{candidate.market}",
                f"- 机会分：{candidate.opportunity_score:.2f}",
                f"- 置信度：{candidate.confidence:.2f}",
                f"- 数据质量：{DATA_QUALITY_LABELS.get(candidate.data_quality, candidate.data_quality)}",
                f"- 证据摘要：{candidate.thesis}",
                f"- 已知风险：{'；'.join(candidate.risks)}",
                "",
                "| 因子组 | 因子 | 分数 | 置信度 | 原始值 | 证据说明 |",
                "| --- | --- | ---: | ---: | ---: | --- |",
                *[
                    (
                        f"| {FACTOR_GROUP_LABELS.get(factor.group, factor.group)} | "
                        f"{factor.name} | {factor.score:.1f} | "
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
        "# 中国ETF专业投资研究报告\n\n"
        f"- 生成时间：{generated_at}\n"
        f"- 运行编号：{screening.run_id}\n"
        f"- 研究周期：{', '.join(horizons)}\n"
        f"- 候选数量：{len(screening.candidates)}\n\n"
        "## 新手阅读指南\n\n"
        "- 先看“智能体研究报告”的总体结论，确认当前适合积极配置、观察，还是暂缓。\n"
        "- 再看“候选标的速览”，把机会分、置信度和数据质量放在一起判断，不要只看排名。\n"
        "- 最后看“技术附录：因子证据表”。附录是给结论溯源用的，不需要逐项背公式。\n"
        "- 仓位区间是风险控制参考，不是适合每个人的个性化配置比例。\n\n"
        "## ETF入门说明\n\n"
        "- ETF，中文常称“交易型开放式指数基金”，可以像股票一样在交易所买卖，"
        "但它通常跟踪一篮子股票、债券、商品或海外指数。\n"
        "- 买入 ETF 不是买单一公司，而是买它跟踪的一组资产。例如沪深300ETF主要跟踪沪深300指数，"
        "芯片ETF主要暴露于半导体产业链。\n"
        "- ETF 的优点是分散、透明、交易方便；缺点是仍会随市场下跌，行业主题 ETF 和跨境 ETF 的波动可能很大。\n"
        "- 新手投资者应优先理解“跟踪指数、持仓方向、波动风险、成交活跃度、费率和折溢价”，"
        "再考虑是否配置。\n\n"
        "## 投资建议口径\n\n"
        "- “优先配置”表示当前证据相对更充分，但仍建议分批、限仓，不代表保证上涨。\n"
        "- “小仓试探”表示机会和风险都较高，只适合用较小仓位验证观点。\n"
        "- “持有观察”表示可以继续跟踪或保留已有仓位，但新增买入需要更多确认信号。\n"
        "- “减仓/回避”表示风险收益比不理想，普通投资者不宜主动增加暴露。\n"
        "- 任何建议都需要同时满足买入前提、仓位上限和退出条件。\n\n"
        "## 数据来源概况\n\n"
        f"{warning_summary}\n\n"
        "## 智能体研究报告\n\n"
        f"{strip_reasoning_blocks(llm_report).strip()}\n\n"
        "## 候选标的速览\n\n"
        "| 排名 | 代码 | 名称 | 机会分 | 置信度 | 数据质量 |\n"
        "| ---: | --- | --- | ---: | ---: | --- |\n"
        f"{table_rows}\n\n"
        "## 技术附录：因子证据表\n\n"
        "这一部分原名 `Structured Evidence`，意思是“结构化证据”。"
        "它记录系统为什么给某个 ETF 打分，例如近期涨跌幅、波动率、最大回撤和成交量变化。"
        "它主要用于复核报告，不是给新手投资者直接做买卖判断的主内容。\n\n"
        "### 术语速查\n\n"
        "- 机会分：系统把趋势、风险、成交活跃度和数据覆盖度合成后的相对排序分数。\n"
        "- 置信度：当前数据能支撑结论的程度，越低越应该保守。\n"
        "- 最大回撤：最近一段时间从高点跌到低点的最大跌幅，用来观察可能承受的亏损压力。\n"
        "- 年化波动率：价格上下波动的剧烈程度，越高越需要降低仓位。\n"
        "- 成交关注度：近期成交量相对历史水平是否放大，放大通常代表市场关注度上升。\n\n"
        "### 完整术语表\n\n"
        "- ETF（交易型开放式指数基金）：可以在交易所买卖、通常跟踪一篮子资产的基金。\n"
        "- 跟踪指数：ETF 试图复制或跟随的指数，例如沪深300、上证50、纳斯达克100。\n"
        "- 宽基 ETF：覆盖较宽市场的 ETF，例如沪深300ETF、上证50ETF，通常比单一行业更分散。\n"
        "- 行业主题 ETF：集中投资某个行业或主题，例如芯片ETF、医疗ETF，弹性更大但风险也更集中。\n"
        "- 跨境 ETF：在境内交易但跟踪海外资产的 ETF，除资产波动外还受汇率、跨境额度和溢价影响。\n"
        "- 仓位：某个标的占全部投资资金的比例。仓位越高，涨跌对账户影响越大。\n"
        "- 止损/退出条件：当事实与原先判断不一致时，用来控制亏损或降低风险的规则。\n"
        "- 折溢价：ETF 市场交易价格相对基金净值的偏离，溢价过高时买入成本可能偏贵。\n"
        "- 成交额/流动性：能否顺利买卖的指标，流动性差时大额交易可能产生更高冲击成本。\n\n"
        f"{factor_sections}\n\n"
        "## 数据源警告明细\n\n"
        f"{warnings}\n\n"
        "## 重要声明\n\n"
        "本报告基于公开数据和本地大模型自动生成，仅供一般性研究参考，"
        "不构成个性化投资建议、收益承诺或自动交易信号。投资者应结合自身风险承受能力、"
        "投资期限和财务状况独立决策，必要时咨询持牌专业人士。\n"
    )


def summarize_warnings(warnings: list[str]) -> str:
    if not warnings:
        return "- 本次运行没有数据源错误或警告。"
    source_counts: dict[str, int] = {}
    cache_count = 0
    for warning in warnings:
        if "_cache:" in warning:
            cache_count += 1
        parts = warning.split(":", 1)[0].split("/", 1)
        source = parts[1] if len(parts) > 1 else "unknown"
        source_counts[source] = source_counts.get(source, 0) + 1
    lines = [
        f"- 数据源警告总数：{len(warnings)}",
        f"- 使用缓存兜底次数：{cache_count}",
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
