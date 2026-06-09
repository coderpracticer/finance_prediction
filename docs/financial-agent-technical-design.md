# 金融投资研究智能体技术方案

版本：0.1  
日期：2026-06-09  
目标用途：个人决策与开发使用  
部署假设：个人本地部署，单用户使用

## 1. 需求结论

本项目目标是构建一个面向个人投资者的主动型投资研究智能体。第一版 MVP 不追求全市场、全资产、全自动交易，而是优先跑通“投资机会筛选”闭环：

1. 从免费公开数据源与网页抓取中获取可用市场数据。
2. 生成多因子综合评分。
3. 输出候选标的列表。
4. 为每个候选标的生成可读的研究解释。
5. 以 Web Dashboard 为主展示结果，并提供 Chat 追问入口。

系统风格偏“机会挖掘型”：允许探索潜在机会和不确定信号，但必须清楚标注证据来源、风险、置信度和数据质量。

## 2. 非目标

MVP 阶段不做：

1. 自动下单或交易执行。
2. 多用户、登录、权限、团队协作。
3. 投资建议合规闭环或投顾资质替代。
4. 高可靠实时行情系统。
5. 对所有市场同时提供深度覆盖。
6. 复杂组合优化、税务优化、衍生品定价。

## 3. 推荐技术栈

### 3.1 总体选择

推荐使用 Python/FastAPI + React/TypeScript + SQLite + APScheduler/Celery-lite 风格任务调度。

理由：

1. 免费金融数据生态更偏 Python，数据处理、网页抓取、因子计算和 Agent 编排更自然。
2. FastAPI 适合本地单用户应用，接口清晰，后续可迁移到云端。
3. React/TypeScript 适合构建 Dashboard + Chat 的组合体验。
4. SQLite 足够支撑个人本地研究，减少部署成本。
5. 任务调度初期可用 APScheduler，后续再升级到 Celery/RQ。

### 3.2 技术栈明细

后端：

- Python 3.11+
- FastAPI
- SQLModel 或 SQLAlchemy + Pydantic
- SQLite
- Pandas / Polars
- BeautifulSoup / selectolax
- httpx
- APScheduler
- LiteLLM 或 OpenAI SDK 作为 LLM 接入层

前端：

- React + TypeScript
- Vite
- TanStack Query
- TanStack Table
- Recharts 或 ECharts
- shadcn/ui 或 Radix UI + Tailwind CSS

开发工具：

- uv 作为 Python 包管理器
- npm/pnpm 作为前端包管理器
- pytest
- ruff
- mypy 可选
- Playwright 用于端到端验证

## 4. 数据源候选清单

用户明确要求第一版保持候选清单，不锁死数据源。因此文档将数据源分为“优先验证”“可替代”“谨慎使用”三类。

### 4.1 行情与基础市场数据

| 数据源 | 覆盖 | 优点 | 风险 | MVP 角色 |
| --- | --- | --- | --- | --- |
| yfinance / Yahoo Finance | 美股、ETF、部分全球市场 | 接入简单，Python 生态成熟 | 非官方接口，稳定性和条款风险较高 | 快速原型候选 |
| Stooq | 美股、指数、部分国际市场 | CSV 获取简单，历史价格友好 | 覆盖和字段有限 | 行情备选 |
| Alpha Vantage | 股票、ETF、技术指标等 | 有官方 API 文档和免费层 | 免费额度有限，频率受限 | 标准化 API 候选 |
| Financial Modeling Prep | 股票、财务、估值等 | 字段丰富，API 友好 | 免费层限制随时间变化 | 基本面候选 |
| Nasdaq Data Link | 多类金融数据 | 数据集多 | 免费数据集质量不一 | 可探索备选 |

### 4.2 财报、公告和监管数据

| 数据源 | 覆盖 | 优点 | 风险 | MVP 角色 |
| --- | --- | --- | --- | --- |
| SEC EDGAR APIs | 美股上市公司 filings、company facts | 官方、稳定、适合基本面研究 | 主要覆盖美国公司 | 强候选 |
| 公司 Investor Relations 页面 | 单家公司公告、presentation | 一手资料 | 网页结构不稳定 | 深度解释时补充 |
| 交易所公告页面 | 不同市场公告 | 一手资料 | 抓取复杂，市场差异大 | 后续扩展 |

### 4.3 新闻、事件和情绪数据

| 数据源 | 覆盖 | 优点 | 风险 | MVP 角色 |
| --- | --- | --- | --- | --- |
| Google News / Bing News 页面抓取 | 宽覆盖 | 事件发现能力强 | 抓取稳定性和合规风险 | 谨慎候选 |
| 新闻站点 RSS | 新闻标题、摘要 | 简单、轻量 | 覆盖不完整 | MVP 候选 |
| 公司新闻稿页面 | 公司事件 | 一手资料 | 抓取成本较高 | 解释补充 |

### 4.4 数据源核验依据

当前公开资料显示：

- SEC 提供 EDGAR APIs，包括 submissions、companyfacts 等接口，适合作为美股公告和财务事实数据来源：[SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)。
- Alpha Vantage 提供官方 API 文档，覆盖时间序列、技术指标等数据：[Alpha Vantage Documentation](https://www.alphavantage.co/documentation/)。
- yfinance 是用于从 Yahoo Finance 下载市场数据的开源工具，但应按个人研究用途谨慎使用，并关注其非官方性质：[yfinance GitHub](https://github.com/ranaroussi/yfinance)。
- Financial Modeling Prep 提供股票、财务和市场数据 API 文档，免费层限制需在实现前再次确认：[Financial Modeling Prep API Docs](https://site.financialmodelingprep.com/developer/docs)。

## 5. MVP 范围

### 5.1 第一版最小闭环

输入：

- 用户配置的市场范围或候选 universe。
- 数据源配置。
- 因子权重配置。
- 每日或手动触发的扫描任务。

处理：

1. 拉取候选标的基础数据。
2. 清洗并标准化字段。
3. 计算价格、动量、估值、质量、成长、事件、风险等因子。
4. 聚合成综合机会分。
5. 选择 Top N 候选。
6. 为候选生成研究解释。
7. 保存结果与证据链。

输出：

- Dashboard 今日机会榜。
- 每个候选的评分拆解。
- 每个候选的一段研究解释。
- 风险点、数据缺口和置信度。
- Chat 追问入口。

### 5.2 MVP 默认 universe

由于标的范围取决于数据可得性，MVP 不固定市场。但建议第一轮验证按以下顺序选择：

1. 美股大盘股 + ETF：数据可得性最好，SEC 数据可补充基本面。
2. 美股 ETF：基本面依赖较少，适合主题和动量筛选。
3. 港股或 A 股：后续根据免费源稳定性扩展。

第一版可以内置一个小规模 universe，例如：

- S&P 500 子集。
- Nasdaq 100 子集。
- 常见美股行业 ETF。

## 6. 系统架构

### 6.1 模块划分

```text
frontend/
  Dashboard
  Candidate Detail
  Chat Panel
  Settings

backend/
  api/
  agents/
  data_sources/
  ingestion/
  factors/
  scoring/
  research/
  scheduler/
  storage/
  eval/

database/
  SQLite

configs/
  data_sources.yaml
  universe.yaml
  factors.yaml
  prompts.yaml
```

### 6.2 数据流

```text
Scheduler / Manual Trigger
  -> Universe Resolver
  -> Data Source Connectors
  -> Raw Data Store
  -> Normalization
  -> Factor Engine
  -> Score Engine
  -> Candidate Selector
  -> Research Agent
  -> Report Store
  -> API
  -> Dashboard / Chat
```

### 6.3 分层职责

数据源层：

- 连接不同免费公开数据源。
- 管理速率限制、重试、缓存。
- 保留原始响应，方便追溯。

标准化层：

- 将不同来源字段映射到统一 schema。
- 处理缺失值、单位、日期、币种。

因子层：

- 只做可解释的计算。
- 每个因子保存原始输入、计算公式、得分和异常标记。

评分层：

- 根据权重合成综合机会分。
- 输出 score、rank、confidence。

Agent 层：

- 根据结构化因子、新闻线索和证据生成自然语言解释。
- 不直接“凭感觉推荐”，必须引用可追溯 evidence。

API 层：

- 提供 Dashboard、详情页、Chat、任务管理和配置接口。

前端层：

- Dashboard 优先。
- Chat 作为候选解释和追问入口。

## 7. 数据库 Schema

SQLite 足够支撑 MVP。建议使用 SQLModel 或 SQLAlchemy 管理。

### 7.1 instruments

记录标的基础信息。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer pk | 内部 ID |
| symbol | text | ticker |
| name | text | 标的名称 |
| asset_type | text | stock / etf / index / fund / crypto |
| market | text | US / HK / CN 等 |
| exchange | text | 交易所 |
| currency | text | 计价货币 |
| sector | text nullable | 行业 |
| industry | text nullable | 子行业 |
| is_active | boolean | 是否启用 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 7.2 data_sources

记录数据源配置和健康状态。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer pk | 数据源 ID |
| name | text | yfinance / sec / alpha_vantage 等 |
| source_type | text | api / scrape / rss / file |
| base_url | text nullable | 基础 URL |
| enabled | boolean | 是否启用 |
| rate_limit_per_min | integer nullable | 频率限制 |
| last_success_at | datetime nullable | 最近成功 |
| last_error_at | datetime nullable | 最近失败 |
| last_error | text nullable | 错误信息 |

### 7.3 raw_snapshots

保留原始数据，便于回溯。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer pk | 快照 ID |
| source_id | integer fk | 数据源 |
| instrument_id | integer fk nullable | 标的 |
| snapshot_type | text | price / financial / news / filing |
| payload_json | json/text | 原始响应 |
| payload_hash | text | 去重哈希 |
| fetched_at | datetime | 拉取时间 |

### 7.4 price_bars

记录标准化行情。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer pk | 行情 ID |
| instrument_id | integer fk | 标的 |
| ts | datetime/date | 时间 |
| timeframe | text | 1d / 1h 等 |
| open | real nullable | 开盘价 |
| high | real nullable | 最高价 |
| low | real nullable | 最低价 |
| close | real | 收盘价 |
| volume | real nullable | 成交量 |
| source_id | integer fk | 数据源 |

索引：

- unique(instrument_id, ts, timeframe, source_id)
- index(instrument_id, ts)

### 7.5 financial_facts

记录基本面事实。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer pk | 事实 ID |
| instrument_id | integer fk | 标的 |
| metric | text | revenue / net_income / eps / pe 等 |
| value | real/text | 指标值 |
| unit | text nullable | 单位 |
| period_start | date nullable | 起始日期 |
| period_end | date nullable | 结束日期 |
| fiscal_period | text nullable | FY / Q1 等 |
| source_id | integer fk | 数据源 |
| raw_snapshot_id | integer fk nullable | 原始快照 |

### 7.6 news_items

记录新闻和事件线索。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer pk | 新闻 ID |
| instrument_id | integer fk nullable | 关联标的 |
| title | text | 标题 |
| url | text | 链接 |
| publisher | text nullable | 来源 |
| published_at | datetime nullable | 发布时间 |
| summary | text nullable | 摘要 |
| sentiment_score | real nullable | 情绪分 |
| novelty_score | real nullable | 新颖度 |
| source_id | integer fk | 数据源 |

### 7.7 factor_scores

记录每个标的每次扫描的因子结果。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer pk | 因子分 ID |
| run_id | integer fk | 扫描任务 |
| instrument_id | integer fk | 标的 |
| factor_name | text | 因子名 |
| raw_value | real/text nullable | 原始值 |
| normalized_score | real | 0-100 |
| confidence | real | 0-1 |
| evidence_json | json/text | 输入证据 |
| warning | text nullable | 数据警告 |

### 7.8 screening_runs

记录每次筛选。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer pk | 运行 ID |
| started_at | datetime | 开始 |
| finished_at | datetime nullable | 结束 |
| status | text | pending / running / success / failed |
| universe_config_json | json/text | universe 配置 |
| factor_config_json | json/text | 因子配置 |
| error | text nullable | 错误 |

### 7.9 candidates

记录入选候选。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer pk | 候选 ID |
| run_id | integer fk | 筛选任务 |
| instrument_id | integer fk | 标的 |
| rank | integer | 排名 |
| opportunity_score | real | 综合机会分 |
| confidence | real | 置信度 |
| thesis | text | 核心投资解释 |
| risks | text | 主要风险 |
| data_quality | text | good / mixed / weak |
| created_at | datetime | 创建时间 |

### 7.10 chat_sessions / chat_messages

用于候选追问。

chat_sessions：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer pk | 会话 ID |
| candidate_id | integer fk nullable | 关联候选 |
| title | text nullable | 标题 |
| created_at | datetime | 创建时间 |

chat_messages：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | integer pk | 消息 ID |
| session_id | integer fk | 会话 |
| role | text | user / assistant / system |
| content | text | 内容 |
| evidence_json | json/text nullable | 引用证据 |
| created_at | datetime | 创建时间 |

## 8. API 设计

### 8.1 Dashboard

`GET /api/dashboard/summary`

返回：

```json
{
  "latest_run_id": 12,
  "run_status": "success",
  "generated_at": "2026-06-09T09:00:00+08:00",
  "candidate_count": 20,
  "data_quality": "mixed",
  "top_themes": ["AI infrastructure", "semiconductor rebound"],
  "warnings": ["Some valuation metrics are missing for ETFs."]
}
```

`GET /api/screening-runs/latest/candidates?limit=20`

返回候选列表：

```json
[
  {
    "candidate_id": 101,
    "symbol": "EXAMPLE",
    "name": "Example Corp",
    "rank": 1,
    "opportunity_score": 84.2,
    "confidence": 0.72,
    "data_quality": "mixed",
    "thesis": "Momentum and earnings revision signals improved...",
    "risks": "Valuation is stretched; news signal is not yet confirmed."
  }
]
```

### 8.2 Candidate Detail

`GET /api/candidates/{candidate_id}`

返回：

- 标的基础信息。
- 综合分。
- 因子分解。
- 研究解释。
- 风险点。
- 相关新闻/filings/价格图数据。

`GET /api/candidates/{candidate_id}/evidence`

返回 evidence 列表，用于解释可追溯性。

### 8.3 Screening Jobs

`POST /api/screening-runs`

手动触发筛选。

`GET /api/screening-runs/{run_id}`

查询任务状态。

`GET /api/screening-runs`

历史运行列表。

### 8.4 Chat

`POST /api/chat/sessions`

创建会话，可关联 candidate。

`POST /api/chat/sessions/{session_id}/messages`

发送追问，后端根据候选结构化数据、因子证据、新闻和财报信息生成回答。

### 8.5 Settings

`GET /api/settings`

读取 universe、数据源、因子权重、调度配置。

`PUT /api/settings`

更新配置。

## 9. 前端页面结构

### 9.1 Dashboard 首页

核心区域：

1. 今日机会榜表格。
2. 机会分、置信度、数据质量。
3. 因子贡献小条形图。
4. 风险标签。
5. 最新扫描状态。
6. 手动刷新按钮。

表格列建议：

- Rank
- Symbol
- Name
- Asset Type
- Opportunity Score
- Confidence
- Top Positive Factors
- Main Risk
- Data Quality
- Updated At

### 9.2 Candidate Detail

模块：

1. 标的概览。
2. 研究解释。
3. 因子雷达图或分组柱状图。
4. 价格走势图。
5. 新闻/公告线索。
6. 风险与反证。
7. Chat 追问面板。

### 9.3 Chat Panel

交互原则：

- Chat 不替代 Dashboard，而是围绕候选标的做追问。
- 回答必须带 evidence summary。
- 对数据缺口要明确说明。

示例问题：

- “为什么它排第一？”
- “最大的反证是什么？”
- “如果只看基本面，它还值得关注吗？”
- “最近新闻信号是否可靠？”

### 9.4 Settings

配置：

- universe 选择。
- 数据源启用/禁用。
- API key 输入。
- 因子权重。
- 扫描频率。
- Top N 数量。

## 10. 任务调度

### 10.1 MVP 调度策略

本地单用户阶段推荐 APScheduler：

- 每日固定时间扫描一次。
- 支持手动触发。
- 支持失败重试。
- 每个数据源设置速率限制。

默认任务：

| 任务 | 频率 | 说明 |
| --- | --- | --- |
| refresh_universe | 每日 | 更新候选 universe |
| fetch_prices | 每日或手动 | 拉取价格数据 |
| fetch_financials | 每周或手动 | 拉取财务指标 |
| fetch_news | 每日 | 拉取新闻/RSS |
| run_screening | 每日或手动 | 计算机会分 |
| generate_research_notes | run_screening 后 | 生成候选解释 |

### 10.2 失败处理

1. 数据源失败不应阻塞整个任务。
2. 每个因子带 confidence。
3. 缺失数据时降权，而不是填充虚假值。
4. Dashboard 显示数据质量和警告。

## 11. Agent 工作流

### 11.1 Agent 角色

建议拆为 4 个轻量 Agent/Workflow，而不是一开始做复杂多 Agent 系统。

Data Analyst：

- 读取结构化数据。
- 解释因子变化。
- 输出事实摘要。

Opportunity Scout：

- 对候选标的进行机会挖掘。
- 聚焦正向催化和潜在拐点。

Risk Challenger：

- 提取反证、风险和数据缺口。
- 防止过度乐观。

Research Writer：

- 汇总成面向个人投资者的可读解释。
- 控制语气：探索机会，但不承诺收益。

### 11.2 工作流

```text
Candidate + Factor Scores + Evidence
  -> Data Analyst fact brief
  -> Opportunity Scout opportunity hypothesis
  -> Risk Challenger counterpoints
  -> Research Writer final note
  -> Save thesis / risks / evidence
```

### 11.3 输出格式

每个候选标的解释建议包含：

1. 一句话机会摘要。
2. 支撑信号。
3. 潜在催化。
4. 主要风险。
5. 数据质量和置信度。
6. 建议追问方向。

示例结构：

```text
EXAMPLE 值得进入观察名单，主要因为短期动量改善、成交活跃度上升，并且近期行业新闻提供了潜在催化。不过估值数据缺失，财务质量信号不足，因此当前更适合作为机会线索，而不是高置信度结论。
```

## 12. 多因子评分设计

### 12.1 因子组

MVP 使用 6 组因子：

1. Momentum：价格趋势和相对强度。
2. Volume/Attention：成交量、换手和关注度异常。
3. Valuation：估值相对水平。
4. Quality：盈利质量和财务稳健性。
5. Growth：收入、利润、EPS 增长。
6. Event/Catalyst：新闻、公告、财报、行业事件。

### 12.2 示例因子

Momentum：

- 20 日收益率。
- 60 日收益率。
- 相对指数收益。
- 价格是否高于 50 日/200 日均线。

Volume/Attention：

- 近 5 日成交量相对 60 日均量。
- 新闻数量变化。
- 搜索/新闻可见度，可选。

Valuation：

- P/E。
- Forward P/E，可选。
- P/S。
- EV/EBITDA，可选。
- ETF 可用费用率、持仓估值替代，MVP 可先缺省。

Quality：

- 毛利率。
- 净利率。
- ROE。
- 自由现金流。
- 负债率。

Growth：

- 收入同比增长。
- EPS 同比增长。
- 利润改善。
- 近期财报 surprise，可选。

Event/Catalyst：

- 近期新闻事件数量。
- 新闻情绪。
- 财报/公告时间临近。
- 行业主题热度。

### 12.3 综合评分

建议初始权重：

| 因子组 | 权重 |
| --- | --- |
| Momentum | 25% |
| Volume/Attention | 15% |
| Valuation | 15% |
| Quality | 15% |
| Growth | 15% |
| Event/Catalyst | 15% |

由于目标偏机会挖掘型，Momentum、Attention、Catalyst 权重略高。后续可在 Settings 中调整。

综合分：

```text
opportunity_score = sum(group_score * group_weight) * confidence_adjustment
```

置信度：

```text
confidence = weighted_average(factor_confidence)
```

数据质量：

- good：关键因子覆盖率 >= 80%。
- mixed：关键因子覆盖率 50%-80%。
- weak：关键因子覆盖率 < 50%。

### 12.4 缺失值策略

1. 不把缺失值当作 0。
2. 缺失因子不参与组内平均。
3. 组内覆盖率过低则降低 confidence。
4. 解释中必须说明关键缺失数据。

## 13. 验证方案

### 13.1 数据验证

检查项：

1. 数据源连接是否成功。
2. 字段是否符合 schema。
3. 日期、币种、单位是否一致。
4. 原始快照是否可追溯。
5. 缺失值是否被正确标记。

### 13.2 因子验证

检查项：

1. 单个因子计算有单元测试。
2. 边界数据不会产生 NaN/Inf。
3. 同一输入重复计算结果一致。
4. 因子分布合理，避免全部集中在极端值。

### 13.3 Agent 输出验证

检查项：

1. 每条解释至少引用 2 类证据，除非数据不足。
2. 不得编造未提供的数据。
3. 必须包含风险或反证。
4. 必须声明数据质量。
5. 对不确定结论使用低置信度表达。

### 13.4 前端验证

检查项：

1. Dashboard 首屏可展示最新候选。
2. 手动触发扫描后状态变化清晰。
3. 候选详情页能展示评分拆解。
4. Chat 能围绕候选追问。
5. 数据源失败时页面不崩溃。

## 14. 项目结构建议

```text
financial-research-agent/
  backend/
    app/
      main.py
      api/
      agents/
      data_sources/
      ingestion/
      factors/
      scoring/
      research/
      scheduler/
      storage/
      models/
      config/
    tests/
    pyproject.toml
  frontend/
    src/
      pages/
      components/
      features/
      api/
      charts/
      stores/
    package.json
  configs/
    data_sources.yaml
    universe.yaml
    factors.yaml
    prompts.yaml
  docs/
  data/
    raw/
    cache/
    app.db
  README.md
```

## 15. 迭代路线

### Phase 0：设计与数据源验证

目标：

- 确认 2-3 个可用数据源。
- 跑通小 universe 的数据获取。
- 建立 schema 和缓存。

交付：

- 数据源验证报告。
- 最小数据表。
- 原始快照保存。

### Phase 1：MVP 筛选闭环

目标：

- 完成多因子计算。
- 生成 Top N 候选。
- 生成候选研究解释。

交付：

- 后端 API。
- SQLite 数据库。
- 手动触发扫描。
- 候选结果落库。

### Phase 2：Dashboard + Detail

目标：

- Dashboard 展示机会榜。
- 候选详情展示因子和解释。
- 显示数据质量和风险。

交付：

- Web UI。
- 图表。
- 配置页面基础版。

### Phase 3：Chat 追问

目标：

- 用户可围绕候选标的追问。
- Chat 回答基于 evidence。

交付：

- Chat session。
- Evidence retrieval。
- 回答格式约束。

### Phase 4：主动监控

目标：

- 每日定时扫描。
- 失败告警。
- 历史运行对比。

交付：

- Scheduler。
- Run history。
- 变化趋势。

### Phase 5：扩展市场与策略

目标：

- 扩展更多市场或 ETF。
- 加入更多因子。
- 做简单回测和命中率评估。

交付：

- Universe 管理。
- 因子权重调参。
- 历史候选表现评估。

## 16. 关键风险

数据源风险：

- 免费数据源不稳定。
- 网页抓取可能受限。
- 免费 API 额度有限。
- 字段变化会破坏解析。

缓解：

- 原始快照落库。
- 数据源适配器隔离。
- 每个数据源做健康检查。
- 支持多个候选数据源。

模型风险：

- LLM 可能过度解释。
- 可能产生没有证据支撑的判断。

缓解：

- 结构化 evidence 输入。
- 输出模板强制风险与数据质量。
- 保存 prompt、输入和输出。
- Agent 输出做规则校验。

投资风险：

- 机会挖掘不等于投资建议。
- 历史信号不保证未来收益。

缓解：

- 明确展示不确定性。
- 强制输出反证和风险。
- 不做自动交易。

## 17. MVP 成功标准

MVP 可视为成功，当满足：

1. 能对一个小规模 universe 完成每日或手动扫描。
2. 能输出 Top 10-20 个候选标的。
3. 每个候选都有可读解释、因子拆解、风险点和数据质量。
4. Dashboard 可用，候选详情可追问。
5. 数据源失败时系统可降级，不直接崩溃。
6. 至少有基础测试覆盖因子计算和 API。
7. 输出内容不会编造不存在的数据。

## 18. 推荐下一步

下一步不是直接搭完整 Web UI，而是做数据源验证 spike：

1. 选 3 个候选数据源做连通性和字段验证。
2. 选择一个小 universe，例如 20-50 个美股大盘股或 ETF。
3. 实现 price + news + basic fundamentals 三类数据的最小 schema。
4. 计算 Momentum、Volume、Event 三组轻量因子。
5. 生成第一版 Top N 和解释。

这能尽快暴露真正的约束：数据能不能拿到、字段是否稳定、免费额度是否够、解释是否有证据支撑。

## 19. 合规与免责声明

该系统应定位为个人投资研究辅助工具，不应包装为自动投顾或确定性买卖建议。所有输出都应包含：

- 数据来源。
- 数据时间。
- 置信度。
- 主要风险。
- 非投资建议提示。

