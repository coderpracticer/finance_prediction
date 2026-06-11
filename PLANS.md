# PLANS

## Current Task: Simplify To CLI Batch Report Generator

- [x] Clarify final product shape: no frontend, no API, no user interaction design.
- [x] Confirm report flow: free public data -> automatic Top N screen -> local LLM report.
- [x] Confirm report outputs: Markdown and PDF by default.
- [x] Confirm Top N behavior: CLI parameter, default 10.
- [x] Confirm LLM behavior: fail fast if local LLM API is unavailable.
- [x] Remove FastAPI/Dashboard entry points from code.
- [x] Add CLI entry point for report generation.
- [x] Add Markdown and PDF report renderers.
- [x] Add `reportlab` dependency for PDF output.
- [x] Update default remote Linux server configuration.
- [x] Expand default universe beyond 10 candidates.
- [x] Update tests away from Web/API assumptions.
- [x] Validate with installed `reportlab` in the project virtual environment.
- [ ] Validate full report generation against the real 2x4090 local LLM API.

## Next Technical Improvements

- [ ] Add a larger configurable US equity/ETF universe file.
- [ ] Add explicit data-source health summary to each report.
- [ ] Add optional JSON artifact for downstream automation.
- [ ] Add retry/backoff controls for public data sources.
- [ ] Add richer short-term and 1-3 month factor sets.
- [ ] Add a scheduled server cron/systemd example after manual generation is stable.
