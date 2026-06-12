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
- Added professional investment team prompt design:
  - `docs/professional-investment-team-prompts-v1.md`
- Upgraded prompt-only team roles for:
  - macro and cross-asset strategy
  - A-share equity analysis
  - China ETF rotation
  - fixed income and FX
  - commodities
  - Crypto
  - news and events
  - risk challenge
  - portfolio sizing
  - compliance review
- Added investment committee style synthesis requirements:
  - rating
  - suggested action
  - sizing range
  - first failure condition
  - ordinary-investor disclaimer
- Diagnosed a generated report under `report/2026-06-12` that used the old US data-source universe:
  - report candidates were AAPL/MSFT/SPY/NVDA-style US symbols
  - warnings referenced Yahoo, Nasdaq, SEC, and Alpha Vantage
  - this matches `configs/data_source_spike.json`, not `configs/china_etf_rotation.json`
- Added runtime progress logging for active config, raw directory, report directory, and universe sample.
- Reviewed the latest China ETF report:
  - data source health showed no warnings
  - the report used China ETF symbols
  - the main quality issue was readability and missing non-price data, not crawler failure
- Improved report readability:
  - renamed `Structured Evidence` to a Chinese technical appendix
  - added a beginner reading guide
  - added terminology explanations for score, confidence, drawdown, volatility, and volume attention
  - made the candidate table include ETF names and Chinese labels
- Replaced US-market residual evidence wording:
  - removed Nasdaq RSS wording from no-news evidence
  - removed SEC companyfacts wording from missing product/fundamental evidence
  - translated default risk notes into Chinese
- Strengthened final report prompts for more detailed beginner-friendly ETF analysis.
- Added non-price data support:
  - ETF product fields in the configured universe
  - config-backed ETF product metadata source
  - CNInfo announcement connector and parser
  - generic product detail storage in `FundamentalSnapshot`
- Added ETF product metadata as a Quality factor, including category, tracking index, theme, and risk profile.
- Added `news_announcement_fundamental_analyst` for news, announcements, and ETF product data.
- Strengthened prompts to require clear but cautious investment advice:
  - suggested action
  - suitable investor profile
  - sizing range
  - entry precondition
  - exit condition
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
3. Check whether the generated report now includes:
   - beginner reading guide
   - longer and clearer ETF explanations
   - ETF product profile evidence such as category, tracking index, theme, and risk profile
   - CNInfo announcement evidence if announcements are returned by the source
   - investment committee rating
   - action and sizing
   - risk and first failure condition
   - Chinese technical appendix instead of `Structured Evidence`
4. Confirm startup logs show:
   - `config=configs/china_etf_rotation.json`
   - `sample=[510050:CN, 510300:CN, ...]`
5. If Eastmoney is rate-limited on the server, add a second China price provider fallback.

## Blockers

- Full end-to-end report generation still requires the local vLLM API to be running.
- Live crawler validation may depend on the server network reaching Eastmoney.

## Validation Results

- `.\.venv\Scripts\python.exe -m unittest tests.test_reports`: 8 tests passed.
- `.\.venv\Scripts\python.exe -m unittest tests.test_reports tests.test_screening_engine`: 14 tests passed.
- `.\.venv\Scripts\python.exe -m unittest tests.test_data_source_spike tests.test_screening_engine tests.test_reports`: 26 tests passed.
- `.\.venv\Scripts\python.exe -m unittest discover -s tests`: 28 tests passed.
- `.\.venv\Scripts\python.exe -m compileall backend`: passed.
- Default config smoke test loaded `configs/china_etf_rotation.json` with 15 CN instruments.
- Enriched config smoke test loaded 15 CN instruments and confirmed ETF metadata fields.
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
