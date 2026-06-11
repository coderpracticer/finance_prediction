# Financial Research Agent

本项目现在是一个本地优先的命令行批处理投资研究报告生成器。

它不再提供前端、Dashboard、FastAPI API 或聊天交互。核心流程是：从免费公开数据源获取历史数据，自动筛选可研究的 Top N 标的，调用远程 Linux 服务器上的本地 OpenAI-compatible LLM，生成 Markdown 和 PDF 投资研究报告。

重要定位：本项目只用于个人投资研究和候选标的优先级排序，不构成投资建议、交易指令或自动交易系统。

## 运行环境

推荐最终部署环境：

- Linux server
- Python 3.11+
- uv
- 可访问外网，用于 Yahoo chart、SEC EDGAR、Nasdaq RSS、Alpha Vantage 等免费公开数据源
- 同机或内网可访问的 OpenAI-compatible 本地 LLM API
- 目标服务器：2 卡 4090，可用于承载本地大模型推理服务

本仓库只负责调用 LLM API，不负责启动具体模型服务。你可以使用 vLLM、llama.cpp server、Ollama OpenAI-compatible endpoint 或其他兼容 `/v1/chat/completions` 的服务。

## 初始化

```bash
cd /home/abc/wxp/finance_prediction
cp .env.example .env
uv venv
source .venv/bin/activate
uv pip install -e .
```

编辑 `.env`：

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

`LOCAL_LLM_BASE_URL` 建议指向同一台 2 卡 4090 Linux 服务器上运行的本地 LLM API。如果模型服务在另一台机器，把地址换成内网可访问地址。

## 生成报告

默认生成 Top 10 候选，并同时输出 Markdown 和 PDF：

```bash
python -m backend.app.cli generate-report
```

等价的 console script：

```bash
fra-report generate-report
```

常用参数：

```bash
python -m backend.app.cli generate-report \
  --top-n 10 \
  --horizons short,medium \
  --config configs/data_source_spike.json \
  --output-dir reports
```

输出示例：

```text
reports/
  2026-06-11/
    investment_report_20260611T091500000000Z.md
    investment_report_20260611T091500000000Z.pdf
```

如果本地 LLM API 不可用、模型名错误、端口错误或返回空内容，命令会直接失败并提示配置问题，不会生成规则 fallback 报告。

## 数据源

当前默认 universe 在 `configs/data_source_spike.json` 中，优先覆盖免费公开数据较稳定的美股/ETF 标的。

当前数据源：

- Yahoo chart endpoint：价格历史
- SEC companyfacts：基本面字段覆盖度
- Nasdaq stock RSS：新闻标题
- Alpha Vantage daily：可选价格 fallback，需要免费 API key
- Stooq：价格 fallback

诊断单个标的：

```bash
python -m backend.app.data_sources.probe AAPL
python -m backend.app.data_sources.probe MSFT
python -m backend.app.data_sources.probe SPY
```

如果服务器 IP 被 Yahoo/Stooq 限制，可以配置 `ALPHA_VANTAGE_API_KEY`。

## 验证

```bash
python -m unittest discover -s tests
python -m compileall backend
```

本地没有安装 `reportlab` 时，PDF 单元测试会跳过；服务器执行 `uv pip install -e .` 后应默认安装并启用 PDF 输出。

## 主要模块

```text
backend/app/cli.py
backend/app/pipeline/report_pipeline.py
backend/app/screening/service.py
backend/app/research/local_llm.py
backend/app/research/prompts.py
backend/app/reports/markdown.py
backend/app/reports/pdf.py
backend/app/data_sources/connectors.py
backend/app/factors/engine.py
backend/app/storage/repository.py
```

## 最小成功路径

```bash
cd /home/abc/wxp/finance_prediction
cp .env.example .env
nano .env
uv venv
source .venv/bin/activate
uv pip install -e .
python -m unittest discover -s tests
python -m backend.app.data_sources.probe AAPL
python -m backend.app.cli generate-report --top-n 10
```
