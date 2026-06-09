# Financial Research Agent

本仓库当前处于 Phase 1 起步：已完成 Phase 0 数据源验证 spike，并开始搭建本地
FastAPI + React MVP 骨架。

## 当前目标

验证免费公开数据源是否足以支撑个人本地投资研究智能体 MVP：

1. 行情数据。
2. 基础财务/公告数据。
3. 新闻或事件线索。
4. 原始快照保存。
5. 数据源验证报告。

## 运行数据源验证

```powershell
python -m backend.app.data_sources.spike `
  --config configs/data_source_spike.json `
  --db data/app.db `
  --raw-dir data/raw/source_spike `
  --report docs/data-source-validation-report.md
```

SEC 建议设置更明确的 User-Agent：

```powershell
$env:SEC_USER_AGENT="FinancialResearchAgent/0.1 your-email@example.com"
```

Alpha Vantage 和 Financial Modeling Prep 当前在配置中默认关闭。若需要验证，可在
`configs/data_source_spike.json` 中启用，并设置：

```powershell
$env:ALPHA_VANTAGE_API_KEY="..."
$env:FMP_API_KEY="..."
```

## 运行测试

```powershell
python -m unittest discover -s tests
```

## 本地 LLM API

研究解释层默认面向 2 卡 4090 服务器上的本地部署 API，按 OpenAI-compatible
`/v1/chat/completions` 接口接入。

```powershell
$env:LOCAL_LLM_BASE_URL="http://<your-4090-server>:8000/v1"
$env:LOCAL_LLM_API_KEY="local"
$env:LOCAL_LLM_MODEL="your-local-model-name"
```

如果本地 LLM API 未启动或调用失败，后端会使用规则模板生成降级研究解释。

## 运行后端

安装依赖后启动：

```powershell
uv pip install -e .
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

手动触发筛选：

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/screening-runs?limit=10"
```

读取最近一次筛选结果：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/screening-runs/latest"
```

围绕候选标的追问：

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/chat/messages" `
  -ContentType "application/json" `
  -Body '{"symbol":"AAPL","message":"最大的反证是什么？"}'
```

## 运行前端

```powershell
cd frontend
npm install
npm run dev
```

当前开发机只需要维护代码；前端依赖安装、构建和本地 LLM 连通性验证可放到 2 卡 4090
服务器上执行。
