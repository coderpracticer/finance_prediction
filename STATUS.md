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

- Real server end-to-end validation is pending until the 2x4090 local LLM API is running.

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
- `python -m unittest discover -s tests`: 15 tests passed.
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
