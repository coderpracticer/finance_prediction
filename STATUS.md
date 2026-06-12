# STATUS

## Done

- Project direction changed from FastAPI Dashboard MVP to CLI batch report generator.
- Removed Web/API source files:
  - `backend/app/main.py`
  - `backend/app/api/routes.py`
  - `backend/app/web/index.html`
- Removed FastAPI/uvicorn/pydantic/httpx runtime dependencies from `pyproject.toml`.
- Added `reportlab` as the default PDF dependency.
- Added console script:
  - `fra-report = backend.app.cli:main`
- Added CLI command:
  - `python -m backend.app.cli generate-report`
  - `fra-report generate-report`
- Added batch report pipeline:
  - `backend/app/pipeline/report_pipeline.py`
- Added strict local LLM report writer:
  - `backend/app/research/local_llm.py`
  - no fallback report when LLM is unavailable
- Added report prompt builder:
  - `backend/app/research/prompts.py`
- Added Markdown/PDF renderers:
  - `backend/app/reports/markdown.py`
  - `backend/app/reports/pdf.py`
- Updated settings for server batch mode:
  - `FRA_REPORT_DIR`
  - default `LOCAL_LLM_BASE_URL=http://127.0.0.1:8001/v1`
  - default `LOCAL_LLM_TIMEOUT_SECONDS=180`
- Removed CORS/Web settings from `.env.example`.
- Expanded default universe in `configs/data_source_spike.json` so `--top-n 10` is feasible.
- Removed chat persistence methods and chat schema from the active SQLite schema.
- Replaced Web tests with report/prompt/CLI tests.
- Rewrote README and server runbook for remote Linux CLI deployment.

## In Progress

- Server report generation works; next quality work should center on crawler price reliability and refining agent prompts from actual report examples.

## Next Actions

1. Install refreshed dependencies in the virtual environment:
   - `uv pip install -e .`
2. Run local validation:
   - `python -m unittest discover -s tests`
   - `python -m compileall backend`
3. On the Linux server, start the local OpenAI-compatible LLM API.
4. Run:
   - `python -m backend.app.cli generate-report --top-n 10`
5. Confirm Markdown and PDF artifacts under `reports/YYYY-MM-DD/`.

## Blockers

- Full end-to-end report generation requires the remote/local LLM API to be running.

## Validation Results

- `uv pip install -e .`: succeeded after allowing uv to use its external cache directory.
- `python -m unittest discover -s tests`: 23 tests passed.
- `python -m compileall backend`: blocked by Windows `__pycache__` write permission on one file.
- Syntax compile without writing `.pyc`: passed.
- `python -m backend.app.cli --help`: CLI help renders successfully.
- Source scan found no active FastAPI/Dashboard/API/chat route references.
- `git status` without safe-directory override is blocked by Git dubious ownership protection; read-only status works with `git -c safe.directory="C:/Users/Administrator/Documents/New project"`.

## Latest Documentation Update

- Simplified `README.md` into a short path:
  - start `vLLM`
  - install project
  - configure `.env`
  - generate report
  - run validation
- Simplified `docs/server-command-runbook.md` with the same vLLM-first deployment flow.
- Kept troubleshooting minimal and command-oriented.
- Updated the vLLM command and `.env` example to use port `8001`.
- Documented that `LOCAL_LLM_MODEL` must match the vLLM `/v1/models` id or `--served-model-name`.
- Improved local LLM HTTP errors to include the actually requested model name.

## Latest Report Quality Update

- Added cached raw snapshot fallback when live Yahoo, Nasdaq RSS, or SEC requests fail.
- Added stronger data-quality handling so missing price history is not scored as neutral.
- Expanded factor evidence:
  - data coverage
  - 5/20/60-day returns
  - 20/60-day moving-average distance
  - annualized volatility
  - 60-day max drawdown
  - downside volatility
  - volume attention
- Strengthened the LLM prompt to produce a deeper Chinese research memo with candidate tiers, short-term and 1-3 month views, first invalidation condition, and follow-up checks.
- Added data-source health and raw factor values to Markdown reports.
- Local cache check confirmed AAPL can read 64 cached Yahoo price rows and compute momentum/risk factors.

## Latest Agent Role Update

- Current previous state: only one real LLM role, the final research writer; factor calculations were deterministic code, not agents.
- Added lightweight multi-agent prompting without adding a heavy agent framework:
  - `data_quality_auditor`
  - `momentum_technical_analyst`
  - `risk_challenger`
  - `opportunity_scout`
  - `final_research_writer`
- Each role uses the same local OpenAI-compatible LLM API with a different system prompt.

## Latest 2026-06-12 Report Review

- Runtime log confirms the full multi-agent chain ran successfully:
  - `data_quality_auditor`
  - `momentum_technical_analyst`
  - `risk_challenger`
  - `opportunity_scout`
  - `final_research_writer`
- Markdown and PDF were generated under `report/2026-06-12`.
- Main quality blocker: all 16 instruments had `prices=0`.
  - Yahoo returned HTTP 403.
  - Alpha Vantage key was not set.
  - Stooq returned an HTML verification page.
  - Cached fallback count was 0 for that run.
- Follow-up fixes applied:
  - Strip `<think>...</think>` reasoning blocks from LLM outputs and Markdown reports.
  - Add news-title samples to event evidence so the LLM does not infer news themes from counts alone.
  - Penalize missing price history by marking low data coverage as `weak` and discounting score.
  - Search sibling raw snapshot directories for cached price/news/fundamental data.

## Latest Critical Path Update

- Elevated the two key project constraints into code and docs:
  - reliable, sufficient price data
  - clear agent roles and prompt boundaries
- Added crawler-first price handling:
  - Yahoo chart crawler
  - Nasdaq historical crawler
  - Alpha Vantage fallback when a key is available
  - Stooq fallback when enabled and reachable
  - raw snapshot cache fallback
- Kept local CSV as optional diagnostics only, not as a project dependency:
  - `FRA_PRICE_CSV_DIR`
  - `--price-csv-dir`
- Added formal report gate:
  - `FRA_REQUIRE_PRICE_HISTORY=true`
  - `FRA_MIN_PRICE_ROWS=60`
  - `FRA_MIN_PRICE_COVERAGE_RATIO=0.8`
  - diagnostics-only bypass: `--allow-weak-price-data`
- Tightened agent prompts with explicit role boundaries:
  - data quality auditor does not discuss opportunities
  - technical analyst only uses technical/data coverage factors
  - risk challenger does not write positive recommendations
  - opportunity scout cannot treat news count as sufficient evidence
- Added `docs/project-critical-path.md`.

## Latest Crawler-Only Constraint Update

- User clarified there is no local market data and prices must be obtained through crawling.
- Updated docs to make crawler retrieval the formal path and local CSV diagnostic-only.
- Added `nasdaq_historical_prices` to `configs/data_source_spike.json`.
- Updated source selection so disabled sources are not attempted.
- Added parser coverage for Nasdaq historical OHLCV JSON.
