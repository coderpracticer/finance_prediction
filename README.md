# Financial Research Agent

本项目是一个本地优先的命令行投资研究报告生成器。

核心流程很简单：

```text
免费公开数据源 -> 本地因子筛选 -> 本地大模型 API -> Markdown/PDF 报告
```

项目只用于个人投资研究和候选标的优先级排序，不构成投资建议、交易指令或自动交易系统。

## 最小运行环境

- Linux server
- Python 3.11+
- uv
- 可访问外网，用于获取公开市场数据
- 本地 OpenAI-compatible LLM API
- 推荐服务器：2 卡 RTX 4090

## 1. 启动本地大模型 API

推荐直接用 `vLLM` 启动 OpenAI-compatible API。

示例：

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

如果使用较小模型，可以把 `--tensor-parallel-size` 改成 `1`。只要服务兼容 `/v1/chat/completions` 即可。

关键点：`--served-model-name` 要和后面 `.env` 里的 `LOCAL_LLM_MODEL` 保持一致。

检查服务：

```bash
curl http://127.0.0.1:8001/v1/models
```

## 2. 安装项目

```bash
cd /home/abc/wxp/finance_prediction
cp .env.example .env
uv venv
source .venv/bin/activate
uv pip install -e .
```

## 3. 配置 `.env`

最小配置如下：

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

如果模型服务在另一台机器，把 `LOCAL_LLM_BASE_URL` 改成内网地址。

如果不确定模型名，先看 vLLM 返回的 id：

```bash
curl http://127.0.0.1:8001/v1/models
```

然后把返回的 `id` 填到 `LOCAL_LLM_MODEL`。

## 4. 运行报告生成

```bash
python -m backend.app.cli generate-report --top-n 10
```

也可以使用 console script：

```bash
fra-report generate-report --top-n 10
```

成功后会输出：

```text
reports/YYYY-MM-DD/investment_report_*.md
reports/YYYY-MM-DD/investment_report_*.pdf
```

正式报告默认要求价格数据覆盖率达标。系统会优先通过网络抓取价格数据：

```bash
python -m backend.app.cli generate-report --top-n 10
```

如果网络价格源暂时不可用，可以使用 `--allow-weak-price-data` 做诊断，但不建议把它作为正式研究输出。价格数据门槛见 [project-critical-path.md](docs/project-critical-path.md)。

## 5. 验证

```bash
python -m unittest discover -s tests
python -m compileall backend
```

## 数据源说明

当前默认配置在 `configs/data_source_spike.json`，主要用于验证免费公开数据源和报告生成闭环。

当前支持：

- Yahoo chart endpoint：价格历史
- SEC companyfacts：美股基本面字段覆盖
- Nasdaq stock RSS：新闻标题
- Alpha Vantage daily：可选价格 fallback
- Stooq：可选价格 fallback

诊断单个标的：

```bash
python -m backend.app.data_sources.probe AAPL
```

## 常见问题

LLM 连接失败：

```bash
curl http://127.0.0.1:8001/v1/models
```

如果报错里出现了一个你没有写进 `.env` 的旧模型名，检查当前 shell 是否有旧环境变量：

```bash
echo $LOCAL_LLM_MODEL
unset LOCAL_LLM_MODEL
```

依赖缺失：

```bash
source .venv/bin/activate
uv pip install -e .
```

数据源被限制：

```bash
nano .env
# 填写 ALPHA_VANTAGE_API_KEY 作为备用价格源
```

报告没有生成：

```bash
find reports -maxdepth 3 -type f | sort | tail
```

## 主要代码位置

```text
backend/app/cli.py
backend/app/pipeline/report_pipeline.py
backend/app/screening/service.py
backend/app/research/local_llm.py
backend/app/research/prompts.py
backend/app/data_sources/connectors.py
backend/app/factors/engine.py
backend/app/reports/
```
