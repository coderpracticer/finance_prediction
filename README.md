# Financial Research Agent

这是一个本地优先的中国ETF风格轮动研究报告生成器。

核心流程很简单：

```text
中国ETF价格爬虫 -> 本地因子筛选 -> 本地大模型多智能体分析 -> Markdown/PDF 报告
```

项目只用于个人投资研究和候选ETF优先级排序，不构成投资建议、交易指令或自动交易系统。

## 运行环境

- Linux server
- Python 3.11+
- uv
- 可访问外网，用于爬取公开价格数据
- 本地 OpenAI-compatible LLM API
- 推荐服务器：2 张 RTX 4090

## 1. 启动本地大模型 API

直接用 `vLLM` 启动 OpenAI-compatible API 即可：

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

检查模型服务：

```bash
curl http://127.0.0.1:8001/v1/models
```

`LOCAL_LLM_MODEL` 必须等于这个接口返回的模型 `id`，或者等于你在 vLLM 启动时设置的 `--served-model-name`。

## 2. 安装项目

```bash
cd /home/abc/wxp/finance_prediction
cp .env.example .env
uv venv
source .venv/bin/activate
uv pip install -e .
```

## 3. 配置 `.env`

最小配置：

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

当前默认研究范围是 A股和中国上市ETF，不做美股预测。默认配置文件是：

```text
configs/china_etf_rotation.json
```

## 4. 生成报告

```bash
python -m backend.app.cli generate-report --top-n 10
```

成功后会输出：

```text
reports/YYYY-MM-DD/investment_report_*.md
reports/YYYY-MM-DD/investment_report_*.pdf
```

正式报告默认要求价格数据过关。如果价格覆盖率不足，系统会停止生成报告，而不是生成一份没有参考价值的报告。

临时诊断可以使用：

```bash
python -m backend.app.cli generate-report --top-n 10 --allow-weak-price-data
```

这个参数只用于排错，不建议作为正式研究输出。

## 5. 验证

```bash
python -m unittest discover -s tests
python -m compileall backend
```

如果 Windows 上 `compileall` 因 `__pycache__` 权限失败，可以用不写 `.pyc` 的语法检查替代。

## 数据源说明

当前中国ETF默认价格源：

- Eastmoney 日线 K 线接口：价格、开高低收、成交量
- raw snapshot 缓存：网络失败时可读取最近一次成功抓取
- 本地 CSV：只作为诊断路径，不作为项目运行前提

旧版报告中大量数据无法获取，主要不是权限问题，而是目标错配：

- Yahoo 经常对服务器 IP 返回 `HTTP 403`
- Stooq 可能返回 HTML verification page
- Alpha Vantage 需要 API key
- SEC 和 Nasdaq RSS 是美股数据源，不适合中国ETF报告

因此新版本默认不再依赖这些美股数据源。

## 核心代码位置

```text
backend/app/cli.py
backend/app/pipeline/report_pipeline.py
backend/app/screening/service.py
backend/app/research/local_llm.py
backend/app/research/prompts.py
backend/app/data_sources/connectors.py
backend/app/factors/engine.py
backend/app/reports/
configs/china_etf_rotation.json
```
