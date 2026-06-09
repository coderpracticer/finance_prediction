# 服务器命令运行清单

当前项目不再需要 Node、npm、React 或 Vite。Dashboard 已内置在 FastAPI 后端里。

默认项目目录：

```bash
/home/abc/wxp/finance_prediction
```

## 0. 进入项目目录

```bash
cd /home/abc/wxp/finance_prediction
pwd
ls
```

应能看到：

```text
backend
configs
docs
pyproject.toml
README.md
```

## 1. 检查基础环境

```bash
python --version
uv --version
```

推荐：

```text
Python >= 3.11
```

如果没有 `uv`：

```bash
pip install uv
```

## 2. 创建配置文件

```bash
cp .env.example .env
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
LOCAL_LLM_MODEL=你的本地模型名
LOCAL_LLM_TIMEOUT_SECONDS=60
```

## 3. 创建目录

```bash
mkdir -p data/raw/mvp
mkdir -p data/raw/source_spike
```

## 4. 安装后端依赖

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

确认导入正常：

```bash
python -c "import backend; print('backend import ok')"
```

运行测试：

```bash
python -m unittest discover -s tests
```

## 5. 启动本地 LLM API

如果你已经有 OpenAI-compatible LLM 服务，只需要确认 `.env`：

```bash
LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1
LOCAL_LLM_MODEL=你的本地模型名
```

可选检查：

```bash
curl http://127.0.0.1:8001/v1/models
```

LLM 暂时不可用也没关系，系统会返回规则降级解释。

## 6. 启动后端和 Dashboard

终端 1：

```bash
cd /home/abc/wxp/finance_prediction
source .venv/bin/activate
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

看到下面内容后，不要关闭这个终端：

```text
Uvicorn running on http://0.0.0.0:8000
Application startup complete.
```

Dashboard 地址：

```text
http://服务器IP:8000/
```

## 7. 检查后端

终端 2：

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

## 8. 诊断数据源

```bash
cd /home/abc/wxp/finance_prediction
source .venv/bin/activate

python -m backend.app.data_sources.probe AAPL
python -m backend.app.data_sources.probe MSFT
python -m backend.app.data_sources.probe SPY
```

如果 Yahoo/Stooq 价格源失败，但 Nasdaq RSS 和 SEC 成功，系统仍可生成候选，只是价格因子置信度会较低。

如果要补齐价格因子，申请 Alpha Vantage free API key，然后写入 `.env`：

```bash
ALPHA_VANTAGE_API_KEY=你的key
```

重启后端后再检查：

```bash
python -m backend.app.data_sources.probe AAPL
```

## 9. 手动运行筛选

```bash
curl -X POST "http://127.0.0.1:8000/api/screening-runs?limit=10"
```

读取最近一次结果：

```bash
curl http://127.0.0.1:8000/api/screening-runs/latest
```

只看候选数量：

```bash
curl -s http://127.0.0.1:8000/api/screening-runs/latest \
  | python -c "import sys,json; d=json.load(sys.stdin); print(d['status'], len(d['candidates']), d.get('warnings', []))"
```

## 10. 测试 Chat

筛选成功后：

```bash
curl -X POST "http://127.0.0.1:8000/api/chat/messages" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","message":"最大的反证是什么？"}'
```

## 11. 打开 Dashboard

浏览器打开：

```text
http://服务器IP:8000/
```

使用顺序：

1. 点击 `Run Screening`。
2. 点击候选标的查看因子、风险和研究解释。
3. 在 `Research Chat` 追问。

## 12. 常见问题排查命令

后端是否活着：

```bash
curl http://127.0.0.1:8000/api/health
```

端口是否占用：

```bash
ss -lntp | grep -E '8000|8001'
```

查看 Python 进程：

```bash
ps aux | grep uvicorn
```

数据库是否生成：

```bash
ls -lh data/app.db
```

原始快照是否生成：

```bash
find data/raw -maxdepth 3 -type f | head
```

查看最近筛选 warning：

```bash
curl -s http://127.0.0.1:8000/api/screening-runs/latest \
  | python -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(d.get('warnings', [])))"
```

## 13. 最小成功路径

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
curl http://127.0.0.1:8000/api/screening-runs/latest
```

浏览器：

```text
http://服务器IP:8000/
```
