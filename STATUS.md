# STATUS

## Done

- Project direction is now focused on A股 and 中国ETF rotation research.
- Default config path changed to:
  - `configs/china_etf_rotation.json`
- Added China ETF universe covering:
  - broad market ETFs
  - dividend/value ETF
  - sector/theme ETFs
  - gold ETF
  - China-listed cross-border ETF
- Added Eastmoney daily kline crawler:
  - source name: `eastmoney_kline_prices`
  - captures date, open, high, low, close, volume
  - writes raw snapshots under `FRA_RAW_DIR`
- Disabled US-only sources in the China ETF config:
  - Yahoo
  - Nasdaq historical
  - Nasdaq RSS
  - SEC companyfacts
  - Alpha Vantage
  - Stooq
- Updated multi-agent prompts:
  - `data_quality_auditor`
  - `china_etf_style_rotation_analyst`
  - `momentum_technical_analyst`
  - `risk_challenger`
  - `opportunity_scout`
  - `final_research_writer`
- Rewrote corrupted Chinese prompt/documentation text.
- Simplified run docs:
  - `README.md`
  - `docs/server-command-runbook.md`
  - `docs/project-critical-path.md`

## In Progress

- Ready for the next full server-side report run with the local vLLM API.

## Next Actions

1. On the Linux server, generate a new report:
   - `python -m backend.app.cli generate-report --top-n 10`
2. Inspect whether `Data Source Health` shows enough price coverage.
3. If Eastmoney is rate-limited on the server, add a second China price provider fallback.

## Blockers

- Full end-to-end report generation still requires the local vLLM API to be running.
- Live crawler validation may depend on the server network reaching Eastmoney.

## Validation Results

- `.\.venv\Scripts\python.exe -m unittest discover -s tests`: 25 tests passed.
- `.\.venv\Scripts\python.exe -m compileall backend`: passed.
- Default config smoke test loaded `configs/china_etf_rotation.json` with 15 CN instruments.
- Live Eastmoney smoke test fetched `510050` with 2535 daily price rows.

## Answer To Current Data-Source Question

- The warnings in the old report are important when they refer to price data. ETF rotation without price history has little research value.
- The old failures were caused by both mismatch and restrictions:
  - The previous default universe and sources were US-oriented.
  - Yahoo can block server IPs with `HTTP 403`.
  - Stooq can return a verification page instead of CSV.
  - Alpha Vantage needs an API key.
  - SEC and Nasdaq RSS are irrelevant for China ETF rotation.
- The new default path uses a China ETF universe and Eastmoney kline crawler first.
