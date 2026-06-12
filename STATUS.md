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

- Real server end-to-end validation of the improved report is pending.

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
- `python -m unittest discover -s tests`: 16 tests passed.
- `python -m compileall backend`: passed.
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
