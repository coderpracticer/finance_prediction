# PLANS

## Current Task: Improve Report Detail And Data Resilience

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
- [x] Simplify README into a short vLLM-first run path.
- [x] Simplify server runbook into environment -> vLLM -> install -> run -> troubleshoot.
- [x] Add cached raw snapshot fallback for price, news, and SEC data.
- [x] Expand factor evidence with data coverage, multi-period momentum, risk, drawdown, and volume.
- [x] Strengthen report prompt for deeper candidate analysis and next-step validation.
- [x] Add data-source health summary and raw factor values to Markdown reports.
- [x] Add regression coverage for Yahoo price parsing and updated factor summary behavior.
- [x] Split one report-writing prompt into lightweight multi-agent prompts.
- [x] Add data quality, momentum, risk, opportunity, and final synthesis roles.
- [x] Validate full report generation against the real 2x4090 local LLM API.
- [x] Inspect generated 2026-06-12 report and runtime log.
- [x] Strip Qwen3 reasoning blocks from final reports.
- [x] Add real news-title samples to event evidence.
- [x] Penalize missing price history as weak data quality.
- [x] Expand cache lookup across sibling raw snapshot directories.
- [x] Add Nasdaq historical crawler as a no-key price fallback.
- [x] Keep local CSV only as an optional diagnostics path.
- [x] Add price-history coverage gate before formal report generation.
- [x] Add explicit agent role boundaries and output contracts.
- [x] Document the two project-critical paths: price data and agent prompting.

## Next Technical Improvements

- [ ] Add ETF rotation MVP docs after the backtest module exists.
- [ ] Add a larger configurable US equity/ETF universe file.
- [x] Add explicit data-source health summary to each report.
- [ ] Add optional JSON artifact for downstream automation.
- [ ] Add retry/backoff controls for public data sources.
- [x] Add richer short-term and 1-3 month factor sets.
- [ ] Add a scheduled server cron/systemd example after manual generation is stable.
- [x] Add an additional crawler-based price provider path for server runs.
