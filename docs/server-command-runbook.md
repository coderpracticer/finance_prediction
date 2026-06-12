# Server Command Runbook

这份 runbook 只保留服务器上最短可执行路径：先启动 `vLLM`，再运行项目。

## 1. 检查环境

```bash
python --version
uv --version
nvidia-smi
```

期望：

```text
Python >= 3.11
uv available
2 x RTX 4090 visible
```

## 2. 启动 vLLM

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /path/to/your/model \
  --served-model-name Qwen/Qwen2.5-1.5B-Instruct \
  --host 0.0.0.0 \
  --port 8001 \
  --max-model-len 131072 \
  --rope-scaling '{"rope_type":"yarn","factor":4.0,"original_max_position_embeddings":32768}' \
  --tensor-parallel-size 2
```

检查：

```bash
curl http://127.0.0.1:8001/v1/models
```

项目只要求兼容：

```text
POST /v1/chat/completions
```

## 3. 安装项目

```bash
cd /home/abc/wxp/finance_prediction
cp .env.example .env
uv venv
source .venv/bin/activate
uv pip install -e .
```

## 4. 配置 `.env`

```bash
FRA_CONFIG_PATH=configs/data_source_spike.json
FRA_DATABASE_PATH=data/app.db
FRA_RAW_DIR=data/raw/mvp
FRA_REPORT_DIR=reports

SEC_USER_AGENT=FinancialResearchAgent/0.1 your-email@example.com
ALPHA_VANTAGE_API_KEY=

LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1
LOCAL_LLM_API_KEY=local
LOCAL_LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct
LOCAL_LLM_TIMEOUT_SECONDS=180
```

`LOCAL_LLM_MODEL` 必须等于 `curl http://127.0.0.1:8001/v1/models` 返回的模型 `id`。最简单做法是在启动 vLLM 时使用 `--served-model-name`，并把 `.env` 写成同一个值。

## 5. 生成报告

```bash
python -m backend.app.cli generate-report --top-n 10
```

成功输出类似：

```text
run_id=...
candidates=10
warnings=...
markdown=reports/YYYY-MM-DD/investment_report_....md
pdf=reports/YYYY-MM-DD/investment_report_....pdf
```

## 6. 本地验证

```bash
python -m unittest discover -s tests
python -m compileall backend
```

## 7. 排错

LLM API 没连上：

```bash
ss -lntp | grep 8001
curl http://127.0.0.1:8001/v1/models
echo $LOCAL_LLM_MODEL
unset LOCAL_LLM_MODEL
```

依赖问题：

```bash
source .venv/bin/activate
uv pip install -e .
```

数据源失败：

```bash
python -m backend.app.data_sources.probe AAPL
```

报告路径：

```bash
find reports -maxdepth 3 -type f | sort | tail
```
