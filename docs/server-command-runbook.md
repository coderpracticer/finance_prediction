# 服务器命令运行清单

适用场景：代码已经上传到 Linux 服务器，需要从零启动后端、前端、数据源验证、筛选和 Chat。

下面命令默认项目目录为：

```bash
/home/abc/wxp/finance_prediction
```

如果你的目录不同，先替换成实际路径。

## 0. 进入项目目录

```bash
cd /home/abc/wxp/finance_prediction
pwd
ls
```

应能看到：

```text
backend
frontend
configs
docs
pyproject.toml
README.md
```

## 1. 检查基础环境

```bash
python --version
node --version
npm --version
uv --version
```

推荐：

```text
Python >= 3.11
Node.js >= 20
npm >= 10
```

如果没有 `uv`：

```bash
pip install uv
```

## 2. 创建配置文件

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env
```

编辑后端环境变量：

```bash
nano .env
```

最少需要改这些：

```bash
FRA_DATABASE_PATH=data/app.db
FRA_RAW_DIR=data/raw/mvp
FRA_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://服务器IP:5173
SEC_USER_AGENT=FinancialResearchAgent/0.1 your-email@example.com
ALPHA_VANTAGE_API_KEY=

LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1
LOCAL_LLM_API_KEY=local
LOCAL_LLM_MODEL=你的本地模型名
LOCAL_LLM_TIMEOUT_SECONDS=60
```

如果浏览器访问的是：

```text
http://192.168.1.20:5173
```

则 `FRA_CORS_ORIGINS` 至少包含：

```bash
FRA_CORS_ORIGINS=http://192.168.1.20:5173,http://localhost:5173,http://127.0.0.1:5173
```

编辑前端环境变量：

```bash
nano frontend/.env
```

如果使用 Vite proxy，保持：

```bash
VITE_API_BASE_URL=
```

如果不用 proxy，浏览器直接访问后端 API，则设置：

```bash
VITE_API_BASE_URL=http://服务器IP:8000
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

确认当前 Python 来自虚拟环境：

```bash
which python
python -c "import backend; print('backend import ok')"
```

运行后端测试：

```bash
python -m unittest discover -s tests
```

预期：

```text
OK
```

## 5. 启动本地 LLM API

本项目假设你的 2 卡 4090 服务器上有 OpenAI-compatible API：

```text
POST /v1/chat/completions
```

如果你已经有服务，只需要确认它的地址和模型名，然后写入 `.env`：

```bash
LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1
LOCAL_LLM_MODEL=你的本地模型名
```

可选检查：

```bash
curl http://127.0.0.1:8001/v1/models
```

如果你的 LLM 服务不支持 `/v1/models`，可以直接测 chat completions：

```bash
curl -X POST "http://127.0.0.1:8001/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer local" \
  -d '{
    "model": "你的本地模型名",
    "messages": [
      {"role": "user", "content": "用一句话回答：你能工作吗？"}
    ],
    "temperature": 0.2
  }'
```

如果本地 LLM 暂时没启动，项目仍能运行，但研究解释会使用规则降级文本。

## 6. 启动后端

开一个终端，执行：

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

这是正常状态，后端会一直等待请求。

## 7. 检查后端

新开一个终端：

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

先不要急着打开前端，先检查数据源。

```bash
cd /home/abc/wxp/finance_prediction
source .venv/bin/activate

python -m backend.app.data_sources.probe AAPL
python -m backend.app.data_sources.probe MSFT
python -m backend.app.data_sources.probe SPY
```

理想输出类似：

```text
PASS AAPL/yahoo_chart_prices: records=64
PASS AAPL/nasdaq_stock_rss: records=15
PASS AAPL/sec_companyfacts: records=503
```

如果看到：

```text
FAIL AAPL/yahoo_chart_prices: HTTPError: HTTP Error 403: Forbidden
```

说明服务器访问该免费数据源被拒绝。此时继续往下跑筛选也可以，系统会尽量使用其它数据源，并在 `warnings` 中标出失败来源。

如果 Yahoo 和 Stooq 都不可用，建议申请 Alpha Vantage free API key，然后写入 `.env`：

```bash
ALPHA_VANTAGE_API_KEY=你的key
```

重启后端后再检查：

```bash
python -m backend.app.data_sources.probe AAPL
```

此时如果配置正确，应看到 `alpha_vantage_daily` 返回 `PASS`。

完整数据源验证：

```bash
python -m backend.app.data_sources.spike \
  --config configs/data_source_spike.json \
  --db data/app.db \
  --raw-dir data/raw/source_spike \
  --report docs/data-source-validation-report.md
```

查看报告：

```bash
sed -n '1,120p' docs/data-source-validation-report.md
```

## 9. 手动运行筛选

```bash
curl -X POST "http://127.0.0.1:8000/api/screening-runs?limit=10"
```

如果成功，会返回：

```json
{
  "run_id": "...",
  "status": "success",
  "candidates": [...]
}
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

读取某个候选详情：

```bash
curl http://127.0.0.1:8000/api/candidates/AAPL
```

## 10. 测试 Chat

筛选成功后，再测候选追问：

```bash
curl -X POST "http://127.0.0.1:8000/api/chat/messages" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","message":"最大的反证是什么？"}'
```

如果本地 LLM 可用，会返回模型生成的回答。

如果本地 LLM 不可用，会返回规则降级回答，这也是预期可用状态。

## 11. 安装前端依赖

新开一个终端：

```bash
cd /home/abc/wxp/finance_prediction/frontend
npm install
```

构建检查：

```bash
npm run build
```

## 12. 启动前端

开发模式：

```bash
cd /home/abc/wxp/finance_prediction/frontend
npm run dev
```

看到类似输出：

```text
Local:   http://localhost:5173/
Network: http://服务器IP:5173/
```

浏览器打开：

```text
http://服务器IP:5173
```

如果打不开，检查服务器防火墙或安全组是否放行 `5173`。

## 13. 前端使用顺序

1. 打开 Dashboard。
2. 如果已有筛选结果，会自动加载最近一次结果。
3. 点击 `Run` 可重新筛选。
4. 点击候选标的查看因子、风险和研究解释。
5. 在 `Research Chat` 输入问题，例如：

```text
最大的反证是什么？
为什么它排名靠前？
如果只看基本面，它还值得观察吗？
```

## 14. 常见问题排查命令

### 后端是否活着

```bash
curl http://127.0.0.1:8000/api/health
```

### 前端是否能访问后端

如果使用 Vite proxy：

```bash
curl http://127.0.0.1:5173/api/health
```

如果使用显式 API：

```bash
curl http://服务器IP:8000/api/health
```

### 端口是否占用

```bash
ss -lntp | grep -E '8000|5173|8001'
```

### 查看 Python 进程

```bash
ps aux | grep uvicorn
```

### 杀掉旧后端

谨慎执行，确认 PID 后再 kill：

```bash
ps aux | grep uvicorn
kill <PID>
```

### 数据库是否生成

```bash
ls -lh data/app.db
```

### 原始快照是否生成

```bash
find data/raw -maxdepth 3 -type f | head
```

### 查看最近筛选 warning

```bash
curl -s http://127.0.0.1:8000/api/screening-runs/latest \
  | python -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(d.get('warnings', [])))"
```

## 15. 最小成功路径

如果只想确认项目能跑，按这个最短路径：

```bash
cd /home/abc/wxp/finance_prediction
cp .env.example .env
cp frontend/.env.example frontend/.env
uv venv
source .venv/bin/activate
uv pip install -e .
python -m unittest discover -s tests
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

新终端：

```bash
cd /home/abc/wxp/finance_prediction
source .venv/bin/activate
curl http://127.0.0.1:8000/api/health
python -m backend.app.data_sources.probe AAPL
curl -X POST "http://127.0.0.1:8000/api/screening-runs?limit=10"
curl http://127.0.0.1:8000/api/screening-runs/latest
```

再新终端：

```bash
cd /home/abc/wxp/finance_prediction/frontend
npm install
npm run dev
```
