# Project Critical Path

这个项目只有两个真正关键的质量门槛。

## 1. 价格数据必须正确且充足

中国ETF轮动研究首先依赖日线价格和成交量。没有足够价格数据，就不应该生成正式报告。

当前默认价格路径：

1. Eastmoney 日线 K 线爬虫
2. 最近一次成功抓取的 raw snapshot 缓存
3. 本地 CSV 诊断路径：`FRA_PRICE_CSV_DIR`

正式报告默认门槛：

```bash
FRA_REQUIRE_PRICE_HISTORY=true
FRA_MIN_PRICE_ROWS=60
FRA_MIN_PRICE_COVERAGE_RATIO=0.8
```

含义：至少 80% 的ETF候选需要有不少于 60 条日线价格记录。

如果不达标，系统会停止生成正式报告。临时排错可以使用：

```bash
python -m backend.app.cli generate-report --top-n 10 --allow-weak-price-data
```

这只用于诊断，不应作为正式研究输出。

旧版报告数据丢失的主要原因：

- 旧 universe 是美股和美股ETF，不是中国ETF。
- Yahoo 在服务器环境容易返回 `HTTP 403`。
- Stooq 可能返回 HTML verification page。
- Alpha Vantage 需要 API key。
- SEC companyfacts 和 Nasdaq RSS 是美股数据源，对A股/中国ETF目标不适配。

所以问题不是单一“网址错了”或“权限限制”，而是数据源选择和研究目标错配，再叠加免费源的反爬/限流。

## 2. 智能体必须分工清楚

当前多智能体是轻量实现：同一个本地 OpenAI-compatible LLM API，通过不同 system prompt 分配角色。

| Agent | 责任 | 边界 |
| --- | --- | --- |
| `data_quality_auditor` | 审计价格覆盖、缓存、warning 和可信度边界 | 只评价数据是否足以支撑研究，不讨论买卖机会 |
| `china_etf_style_rotation_analyst` | 比较宽基、红利、行业主题、商品和跨境ETF的相对强弱 | 只讨论A股和中国上市ETF，不做美股个股预测 |
| `momentum_technical_analyst` | 分析收益、均线、成交量、波动和回撤 | 只使用结构化技术面证据 |
| `risk_challenger` | 寻找反证、数据缺口和第一否定条件 | 不写正向推荐 |
| `opportunity_scout` | 提炼研究优先级、Why now 和验证动作 | 不把新闻数量当成充分投资理由 |
| `final_research_writer` | 综合前面结论生成中文报告 | 保留数据限制，不给确定性买卖建议 |

原则：

- Agent 只能使用结构化证据。
- 研究范围限定为A股和中国上市ETF。
- 跨境ETF可以作为中国上市ETF品种分析，但不扩展到美股个股预测。
- 输出不得包含 `<think>` 或内部推理草稿。
- 最终报告是研究优先级，不是投资建议或交易指令。
