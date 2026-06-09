# Financial Research Agent

面向个人投资者的本地优先投资研究智能体 MVP。

当前版本只有一个服务：FastAPI 后端。Dashboard 已内置在后端中，不再需要 Node、npm、React 或 Vite。

浏览器直接打开：

```text
http://服务器IP:8000/
```

重要定位：本项目是个人投资研究辅助工具，不是自动交易系统，也不构成投资建议。

## 1. 前置条件

推荐服务器环境：

- Linux server
- Python 3.11+
- uv
- 可访问外网，用于访问 Yahoo chart、SEC EDGAR、Nasdaq RSS、Alpha Vantage 等公开数据源
- 可选：本地 OpenAI-compatible LLM API，运行在 2 卡 4090 服务器上

检查命令：

```bash
python --version
uv --version
```

如果没有 `uv`：

```bash
pip install uv
```

更细命令清单见：

```text
docs/server-command-runbook.md
```

## 2. 初始化项目

进入项目根目录：

```bash
cd /home/abc/wxp/finance_prediction
```

创建环境配置：

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
nano .env
```

建议配置：

```bash
FRA_DATABASE_PATH=data/app.db
FRA_RAW_DIR=data/raw/mvp
FRA_CORS_ORIGINS=http://服务器IP:8000,http://localhost:8000,http://127.0.0.1:8000
SEC_USER_AGENT=FinancialResearchAgent/0.1 your-email@example.com
ALPHA_VANTAGE_API_KEY=

LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1
LOCAL_LLM_API_KEY=local
LOCAL_LLM_MODEL=your-local-model-name
LOCAL_LLM_TIMEOUT_SECONDS=60
```

说明：

- `LOCAL_LLM_BASE_URL` 指向本地 LLM 的 OpenAI-compatible endpoint。
- 后端会调用 `${LOCAL_LLM_BASE_URL}/chat/completions`。
- 如果 LLM API 暂时不可用，系统会自动使用规则模板生成降级解释。
- 如果服务器 IP 访问 Yahoo/Stooq 价格源被 403，可以设置 `ALPHA_VANTAGE_API_KEY` 作为价格 fallback。

## 3. 安装后端依赖

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

运行测试：

```bash
python -m unittest discover -s tests
```

预期：

```text
OK
```

## 4. 启动后端与 Dashboard

```bash
source .venv/bin/activate
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

看到下面内容后，不要关闭这个终端：

```text
Uvicorn running on http://0.0.0.0:8000
Application startup complete.
```

浏览器打开：

```text
http://服务器IP:8000/
```

## 5. 检查服务

新开终端：

```bash
curl http://127.0.0.1:8000/api/health
```

预期：

```json
{"status":"ok"}
```

查看配置：

```bash
curl http://127.0.0.1:8000/api/settings
```

## 6. 诊断数据源

```bash
source .venv/bin/activate

python -m backend.app.data_sources.probe AAPL
python -m backend.app.data_sources.probe MSFT
python -m backend.app.data_sources.probe SPY
```

如果 Yahoo/Stooq 价格源失败，但 Nasdaq RSS 和 SEC 成功，系统仍可生成候选，只是价格因子置信度会较低。

若想补齐价格因子，申请 Alpha Vantage free API key 后写入 `.env`：

```bash
ALPHA_VANTAGE_API_KEY=你的key
```

然后重启后端。

## 7. 手动运行筛选

```bash
curl -X POST "http://127.0.0.1:8000/api/screening-runs?limit=10"
```

读取最近一次结果：

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

## 8. 常用 API

| Method | Path | 用途 |
| --- | --- | --- |
| GET | `/` | 内置 Dashboard |
| GET | `/api/health` | 健康检查 |
| GET | `/api/settings` | 查看运行配置摘要 |
| POST | `/api/screening-runs?limit=10` | 手动触发筛选 |
| GET | `/api/screening-runs/latest` | 读取最近一次筛选结果 |
| GET | `/api/candidates/{symbol}` | 读取候选详情 |
| POST | `/api/chat/messages` | 围绕候选标的追问 |

## 9. 生成的数据

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

## 10. 常见问题

### 浏览器打不开 Dashboard

确认后端已启动：

```bash
curl http://127.0.0.1:8000/api/health
```

确认服务器防火墙或安全组放行 `8000`。

浏览器访问：

```text
http://服务器IP:8000/
```

### 数据源 403

先运行：

```bash
python -m backend.app.data_sources.probe AAPL
```

如果 Yahoo/Stooq 都失败，配置 `ALPHA_VANTAGE_API_KEY`。

### 本地 LLM 没有回答

检查：

```bash
curl http://127.0.0.1:8001/v1/models
```

如果你的 LLM server 不提供 `/v1/models`，至少确认 `/v1/chat/completions` 可用。

LLM 不可用时，系统仍会返回规则降级解释。

## 11. 最小成功路径

终端 1：

```bash
cd /home/abc/wxp/finance_prediction
cp .env.example .env
uv venv
source .venv/bin/activate
uv pip install -e .
python -m unittest discover -s tests
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

终端 2：

```bash
cd /home/abc/wxp/finance_prediction
source .venv/bin/activate
curl http://127.0.0.1:8000/api/health
python -m backend.app.data_sources.probe AAPL
curl -X POST "http://127.0.0.1:8000/api/screening-runs?limit=10"
```

浏览器：

```text
http://服务器IP:8000/
```
