# Financial Research Agent

面向个人投资者的本地优先投资研究智能体 MVP。

当前版本支持：

1. 从免费公开数据源抓取小规模 universe 的行情、SEC companyfacts 和 Nasdaq RSS 新闻。
2. 计算 Momentum、Volume/Attention、Event/Catalyst、Quality 覆盖度等轻量因子。
3. 生成 Top N 投资机会候选。
4. 将筛选结果、候选标的、因子分数和 Chat 消息保存到 SQLite。
5. 通过本地 OpenAI-compatible LLM API 生成研究解释和候选追问回答。
6. 提供 FastAPI 后端和 React Dashboard 前端。

重要定位：本项目是个人投资研究辅助工具，不是自动交易系统，也不构成投资建议。

## 1. 目录结构

```text
backend/
  app/
    api/              FastAPI routes
    config/           runtime settings
    data_sources/     free data source connectors
    factors/          factor calculation
    models/           dataclass schemas
    research/         local LLM research writer
    screening/        screening workflow
    storage/          SQLite schema and repository
configs/
  data_source_spike.json
frontend/
  src/
    api/
    components/
    pages/
docs/
tests/
```

## 2. 前置条件

推荐服务器环境：

- Linux server
- Python 3.11+
- Node.js 20+
- npm 10+
- uv
- 可访问外网，用于访问 Yahoo chart、SEC EDGAR、Nasdaq RSS
- 本地 OpenAI-compatible LLM API，运行在 2 卡 4090 服务器上

检查命令：

```bash
python --version
node --version
npm --version
uv --version
```

如果没有 `uv`，可按你的服务器规范安装。常见方式：

```bash
pip install uv
```

## 3. 初始化项目

进入项目根目录：

```bash
cd financial-research-agent
```

创建环境配置：

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

编辑 `.env`：

```bash
nano .env
```

至少需要确认这些配置：

```bash
FRA_DATABASE_PATH=data/app.db
FRA_RAW_DIR=data/raw/mvp
FRA_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://<server-ip>:5173
SEC_USER_AGENT=FinancialResearchAgent/0.1 your-email@example.com

LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1
LOCAL_LLM_API_KEY=local
LOCAL_LLM_MODEL=your-local-model-name
LOCAL_LLM_TIMEOUT_SECONDS=60
```

说明：

- `LOCAL_LLM_BASE_URL` 必须指向本地 LLM 的 OpenAI-compatible endpoint。
- 后端会调用 `${LOCAL_LLM_BASE_URL}/chat/completions`。
- 如果 LLM API 暂时不可用，系统会自动使用规则模板生成降级解释。
- `FRA_CORS_ORIGINS` 需要包含浏览器访问前端时使用的地址。

## 4. 安装后端依赖

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

运行测试：

```bash
python -m unittest discover -s tests
```

预期结果类似：

```text
Ran 9 tests
OK
```

## 5. 启动后端

开发启动：

```bash
source .venv/bin/activate
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

预期返回：

```json
{"status":"ok"}
```

查看当前配置摘要：

```bash
curl http://127.0.0.1:8000/api/settings
```

## 6. 安装并启动前端

新开一个终端：

```bash
cd frontend
npm install
npm run dev
```

Vite 默认监听：

```text
http://<server-ip>:5173
```

当前 `frontend/vite.config.ts` 已配置：

- `host: 0.0.0.0`
- dev proxy: `/api -> http://127.0.0.1:8000`

因此默认情况下 `frontend/.env` 可以保持：

```bash
VITE_API_BASE_URL=
```

如果你不用 Vite proxy，而是让浏览器直接访问后端 API，可以设置：

```bash
VITE_API_BASE_URL=http://<server-ip>:8000
```

修改后需要重启前端 dev server。

## 7. 首次运行筛选

后端启动后，可以手动触发一次筛选：

```bash
curl -X POST "http://127.0.0.1:8000/api/screening-runs?limit=10"
```

读取最近一次筛选结果：

```bash
curl http://127.0.0.1:8000/api/screening-runs/latest
```

读取某个候选标的：

```bash
curl http://127.0.0.1:8000/api/candidates/AAPL
```

围绕候选标的追问：

```bash
curl -X POST "http://127.0.0.1:8000/api/chat/messages" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","message":"最大的反证是什么？"}'
```

## 8. 数据源验证

如果你想先检查免费数据源是否可用：

```bash
python -m backend.app.data_sources.spike \
  --config configs/data_source_spike.json \
  --db data/app.db \
  --raw-dir data/raw/source_spike \
  --report docs/data-source-validation-report.md
```

验证报告会写入：

```text
docs/data-source-validation-report.md
```

原始快照会写入：

```text
data/raw/source_spike/
```

## 9. 本地 LLM API 要求

后端假设本地 LLM 服务提供 OpenAI-compatible Chat Completions API：

```text
POST /v1/chat/completions
```

请求格式类似：

```json
{
  "model": "your-local-model-name",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.4
}
```

响应需要包含：

```json
{
  "choices": [
    {
      "message": {
        "content": "..."
      }
    }
  ]
}
```

可用的本地推理框架包括但不限于 vLLM、LMDeploy、Ollama OpenAI-compatible server 等。只要 endpoint 兼容即可。

## 10. 常用 API

| Method | Path | 用途 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| GET | `/api/settings` | 查看运行配置摘要 |
| POST | `/api/screening-runs?limit=10` | 手动触发筛选 |
| GET | `/api/screening-runs/latest` | 读取最近一次筛选结果 |
| GET | `/api/candidates/{symbol}` | 读取候选详情 |
| POST | `/api/chat/messages` | 围绕候选标的追问 |

## 11. 配置 universe

当前 universe 在：

```text
configs/data_source_spike.json
```

示例：

```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "market": "US",
  "stooq_symbol": "aapl.us",
  "cik": "0000320193"
}
```

说明：

- `symbol` 用于 Yahoo chart 和 Nasdaq RSS。
- `cik` 用于 SEC companyfacts。
- ETF 或没有 SEC CIK 的标的可以将 `cik` 设置为 `null`。

## 12. 生成的数据

运行后会产生：

```text
data/app.db
data/raw/mvp/
data/raw/source_spike/
```

这些属于本地运行数据，默认已在 `.gitignore` 中忽略。

SQLite 中的核心表：

- `screening_runs`
- `candidates`
- `factor_scores`
- `chat_sessions`
- `chat_messages`

## 13. 常见问题

### 前端页面打不开

确认前端监听地址：

```bash
npm run dev
```

确认服务器安全组或防火墙放行 `5173`。

### 前端能打开但 API 失败

确认后端启动：

```bash
curl http://127.0.0.1:8000/api/health
```

如果使用显式 API 地址，检查 `frontend/.env`：

```bash
VITE_API_BASE_URL=http://<server-ip>:8000
```

如果使用 Vite proxy，保持：

```bash
VITE_API_BASE_URL=
```

### CORS 报错

编辑 `.env`：

```bash
FRA_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://<server-ip>:5173
```

然后重启后端。

### SEC 请求失败

设置更明确的 User-Agent：

```bash
SEC_USER_AGENT=FinancialResearchAgent/0.1 your-email@example.com
```

然后重启后端。

### 本地 LLM 没有回答

检查：

```bash
curl http://127.0.0.1:8001/v1/models
```

如果你的 LLM server 不提供 `/v1/models`，至少确认 `/v1/chat/completions` 可用，并检查：

```bash
LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1
LOCAL_LLM_MODEL=your-local-model-name
```

LLM 不可用时，系统仍会返回规则降级解释。

## 14. 推荐启动顺序

1. 启动本地 LLM API。
2. 启动 FastAPI 后端。
3. 运行一次 `POST /api/screening-runs`。
4. 启动前端 Dashboard。
5. 在候选详情页中追问研究问题。

