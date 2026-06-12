# Server Command Runbook

这份 runbook 只保留服务器上最短可执行路径：启动 `vLLM`，安装项目，生成中国ETF研究报告。

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
  --model /home/ma-user/work/dataset/harness_summary/models/Qwen8B \
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
FRA_CONFIG_PATH=configs/china_etf_rotation.json
FRA_DATABASE_PATH=data/app.db
FRA_RAW_DIR=data/raw/mvp
FRA_REPORT_DIR=reports
FRA_REQUIRE_PRICE_HISTORY=true
FRA_MIN_PRICE_ROWS=60
FRA_MIN_PRICE_COVERAGE_RATIO=0.8

LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1
LOCAL_LLM_API_KEY=local
LOCAL_LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct
LOCAL_LLM_TIMEOUT_SECONDS=180
```

`LOCAL_LLM_MODEL` 必须等于：

```bash
curl http://127.0.0.1:8001/v1/models
```

返回的模型 `id`。

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

## 6. 排错

LLM API 没连上：

```bash
ss -lntp | grep 8001
curl http://127.0.0.1:8001/v1/models
echo $LOCAL_LLM_MODEL
unset LOCAL_LLM_MODEL
```

价格数据不足：

```bash
python -m backend.app.cli generate-report --top-n 10 --allow-weak-price-data
```

如果加上 `--allow-weak-price-data` 才能生成，说明价格源没有稳定拿到足够日线数据，报告只能用于诊断。

依赖问题：

```bash
source .venv/bin/activate
uv pip install -e .
```

本地验证：

```bash
python -m unittest discover -s tests
python -m compileall backend
```
