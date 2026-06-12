# Project Critical Path

本项目只有两个核心质量门槛。

## 1. 价格数据必须可靠

没有正确且充足的价格数据，就不应生成正式研究报告。

正式价格数据必须通过网络抓取获得。本地文件只用于调试、复现或临时兜底，不作为项目运行前提。

价格数据优先级：

1. Yahoo chart crawler
2. Nasdaq historical crawler
3. Alpha Vantage crawler/API fallback
4. Stooq crawler fallback
5. 最近 raw snapshot 缓存
6. 本地 CSV，可选诊断路径：`FRA_PRICE_CSV_DIR`

默认门槛：

```bash
FRA_REQUIRE_PRICE_HISTORY=true
FRA_MIN_PRICE_ROWS=60
FRA_MIN_PRICE_COVERAGE_RATIO=0.8
```

可选本地 CSV 格式：

```csv
Date,Open,High,Low,Close,Volume
2026-06-10,100,103,99,102,1000
2026-06-11,102,105,101,104,1200
```

文件名示例：

```text
data/prices/AAPL.csv
data/prices/MSFT.csv
data/prices/SPY.csv
```

如果价格覆盖率不过关，默认直接停止生成报告。这是项目的质量门槛，不建议长期关闭。

调试时可以临时使用：

```bash
python -m backend.app.cli generate-report --top-n 10 --allow-weak-price-data
```

这只能用于诊断，不应作为正式研究输出。

## 2. 智能体必须分工清楚

当前使用同一个本地 LLM API，通过不同 system prompt 实现轻量多智能体。

角色：

| Agent | 责任 | 边界 |
| --- | --- | --- |
| `data_quality_auditor` | 审计数据覆盖、缓存、warning 和可信度边界 | 只评价数据是否足以支撑研究，不讨论买卖机会 |
| `momentum_technical_analyst` | 分析收益、均线、成交量、波动和回撤 | 只使用技术面和数据覆盖因子 |
| `risk_challenger` | 寻找反证、数据缺口和第一否定条件 | 不写正向推荐 |
| `opportunity_scout` | 提炼研究优先级、Why now 和验证动作 | 不把新闻数量当成充分投资理由 |
| `final_research_writer` | 综合前面结论生成中文报告 | 保留数据限制，不给确定性买卖建议 |

原则：

- Agent 只能使用结构化证据。
- 新闻分析必须基于新闻标题样例，不能只根据新闻数量推断主题。
- 输出不得包含 `<think>` 或内部推理草稿。
- 最终报告是研究优先级，不是投资建议或交易指令。
