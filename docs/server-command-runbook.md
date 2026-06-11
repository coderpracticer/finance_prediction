# Server Command Runbook

面向远程 2 卡 4090 Linux 服务器的命令行部署清单。

## 1. 基础环境

```bash
python --version
uv --version
nvidia-smi
```

建议：

```text
Python >= 3.11
uv available
2 x RTX 4090 visible in nvidia-smi
```

## 2. 安装项目

```bash
cd /home/abc/wxp/finance_prediction
cp .env.example .env
nano .env
uv venv
source .venv/bin/activate
uv pip install -e .
```

推荐 `.env`：

```bash
FRA_CONFIG_PATH=configs/data_source_spike.json
FRA_DATABASE_PATH=data/app.db
FRA_RAW_DIR=data/raw/mvp
FRA_REPORT_DIR=reports

SEC_USER_AGENT=FinancialResearchAgent/0.1 your-email@example.com
ALPHA_VANTAGE_API_KEY=

LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1
LOCAL_LLM_API_KEY=local
LOCAL_LLM_MODEL=your-local-model-name
LOCAL_LLM_TIMEOUT_SECONDS=180
```

## 3. 启动或确认本地 LLM API

项目要求一个 OpenAI-compatible endpoint：

```text
POST /v1/chat/completions
```

可选检查：

```bash
curl http://127.0.0.1:8001/v1/models
```

有些推理服务不实现 `/v1/models`，但必须实现 `/v1/chat/completions`。

## 4. 数据源诊断

```bash
source .venv/bin/activate
python -m backend.app.data_sources.probe AAPL
python -m backend.app.data_sources.probe MSFT
python -m backend.app.data_sources.probe SPY
```

如果价格源被限制：

```bash
nano .env
# set ALPHA_VANTAGE_API_KEY=your-free-key
```

## 5. 生成报告

```bash
python -m backend.app.cli generate-report --top-n 10
```

指定输出目录：

```bash
python -m backend.app.cli generate-report \
  --top-n 10 \
  --horizons short,medium \
  --output-dir reports
```

成功输出：

```text
run_id=...
candidates=10
warnings=...
markdown=reports/YYYY-MM-DD/investment_report_....md
pdf=reports/YYYY-MM-DD/investment_report_....pdf
```

## 6. 验证

```bash
python -m unittest discover -s tests
python -m compileall backend
```

## 7. 常见排查

LLM 连接失败：

```bash
ss -lntp | grep 8001
curl http://127.0.0.1:8001/v1/models
```

依赖缺失：

```bash
source .venv/bin/activate
uv pip install -e .
```

数据库是否生成：

```bash
ls -lh data/app.db
```

报告是否生成：

```bash
find reports -maxdepth 3 -type f | sort | tail
```

原始数据快照：

```bash
find data/raw -maxdepth 3 -type f | head
```
