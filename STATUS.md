# STATUS

## Done

- 已通过连续追问明确项目目标：
  - 面向个人投资者。
  - 投资研究场景。
  - 主动型研究助理。
  - MVP 优先做投资机会筛选。
  - 使用多因子综合打分。
  - 每个候选标的需要可读研究解释。
  - 偏机会挖掘型。
  - 数据源优先免费公开数据源与网页抓取。
  - Web 应用形态，Dashboard 优先，Chat 辅助。
  - 从零开始做技术方案和项目结构。
  - 默认个人本地部署、单用户使用。
  - 数据源先保留候选清单，不锁死第一版实现。
- 已创建技术方案文档：
  - `docs/financial-agent-technical-design.md`
- 已创建计划文档：
  - `PLANS.md`
- 已执行 Phase 0 数据源验证 spike：
  - 创建 `configs/data_source_spike.json`
  - 创建 `backend/app/data_sources/spike.py`
  - 创建 `backend/app/storage/source_spike_schema.sql`
  - 创建 `docs/data-source-validation-report.md`
  - 创建 `tests/test_data_source_spike.py`
- 已验证当前小 universe：
  - AAPL
  - MSFT
  - SPY
- 当前可用数据源组合：
  - price: Yahoo chart endpoint
  - fundamentals: SEC companyfacts
  - news: Nasdaq stock RSS
- 已添加 `.gitignore`，避免提交本地数据库和原始快照。
- 已搭建 FastAPI MVP 骨架：
  - 后端入口：`backend/app/main.py`
  - API 路由：`backend/app/api/routes.py`
  - 数据源 connector：`backend/app/data_sources/connectors.py`
  - 因子引擎：`backend/app/factors/engine.py`
  - 筛选服务：`backend/app/screening/service.py`
  - 本地 LLM 研究解释：`backend/app/research/local_llm.py`
  - 内置 Dashboard：`backend/app/web/index.html`
- 已按 2 卡 4090 本地部署 API 设计 LLM 接入：
  - `LOCAL_LLM_BASE_URL`
  - `LOCAL_LLM_API_KEY`
  - `LOCAL_LLM_MODEL`
- 已实现本地 LLM API 不可用时的规则解释降级。
- 已创建项目虚拟环境 `.venv` 并安装后端依赖。
- 已按“当前电脑只写代码，服务器上运行验证”的约束调整工作重点。
- 已实现正式持久化与读取：
  - `backend/app/storage/mvp_schema.sql`
  - `backend/app/storage/repository.py`
  - `GET /api/screening-runs/latest`
  - `GET /api/candidates/{symbol}`
- 已实现候选标的追问接口：
  - `POST /api/chat/messages`
- 已实现内置 Dashboard 自动加载最近筛选结果和候选 Chat 面板。
- 已移除 Node/npm/Vite/React 前端依赖，当前只需启动 FastAPI 后端即可使用 Dashboard。
- 已完善从零使用说明：
  - 后端环境准备
  - 前端启动
  - 本地 LLM API 配置
  - 首次筛选
  - 数据源验证
  - 常见问题
- 已新增环境模板：
  - `.env.example`
  - `frontend/.env.example`
- 已支持 `.env` 自动加载和可配置 CORS：
  - `FRA_CORS_ORIGINS`
- 已增强服务器数据源排障能力：
  - 单个数据源失败不再拖垮整个标的。
  - Yahoo chart 增加 query1/query2 fallback。
  - price 失败时尝试 Stooq fallback。
  - warnings 会标明具体失败数据源。
  - 新增 `python -m backend.app.data_sources.probe SYMBOL`。

## In Progress

- 暂无。

## Next Actions

1. 接入并验证真实 2 卡 4090 本地 LLM API 的研究解释输出。
2. 在服务器上打开 `http://服务器IP:8000/` 验证内置 Dashboard。
3. 在服务器上跑真实 screening + local LLM chat 联调。
4. 继续扩展正式 settings 页面和 universe 管理。

## Blockers

- 暂无。

## Validation Results

- 已检查文档文件存在与章节结构。
- 已运行 `python -m unittest discover -s tests`：4 tests passed。
- 已运行 `.venv\Scripts\python -m unittest discover -s tests`：9 tests passed。
- 已运行 `.venv\Scripts\python -m compileall backend`：通过。
- 已运行真实数据源验证命令：
  - `python -m backend.app.data_sources.spike --config configs/data_source_spike.json --db data/app.db --raw-dir data/raw/source_spike --report docs/data-source-validation-report.md`
- 已运行一次真实筛选闭环：
  - status: success
  - candidates: 2
  - AAPL: 74.62, data_quality=good
  - SPY: 59.97, data_quality=mixed
- 已用 FastAPI TestClient 验证：
  - `/api/health`
  - `/api/settings`
  - `/api/screening-runs/latest`
  - `/api/chat/messages` 参数校验
- FastAPI 前台启动验证通过：`uvicorn` 可启动到 `http://127.0.0.1:8000`。
- 已用 FastAPI TestClient 验证 `/` 内置 Dashboard 可返回 HTML。
- 最新数据源验证报告摘要：
  - passed: 8
  - partial: 0
  - weak: 0
  - failed: 0
  - skipped: 1
- `SPY` 的 SEC companyfacts 被跳过，因为当前配置没有 CIK，这是预期结果。
- `git status --short` 未能完成：Git 检测到当前仓库存在 dubious ownership，需要用户自行决定是否添加 `safe.directory`。
