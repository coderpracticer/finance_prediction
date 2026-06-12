# PLANS

## Current Task: Refocus Report System On China ETF Rotation

- [x] Identify why the latest report has low readability and reference value.
- [x] Confirm project scope: A股 and 中国ETF only, no US stock prediction.
- [x] Add China ETF universe configuration.
- [x] Add Eastmoney daily kline price crawler.
- [x] Keep local CSV as diagnostics only, not a required data input.
- [x] Disable US-only sources in the China ETF default config.
- [x] Update default config path to `configs/china_etf_rotation.json`.
- [x] Rewrite agent prompts with clean Chinese text.
- [x] Add China ETF style-rotation agent role.
- [x] Update report title and final-writer scope.
- [x] Simplify README and server runbook.
- [x] Update critical-path documentation.
- [x] Run unit tests.
- [x] Run syntax validation.
- [x] Smoke-test live Eastmoney price fetch for one China ETF.

## Current Task: Upgrade To Professional Investment Team Prompts

- [x] Write v1 professional investment team prompt design document.
- [x] Expand agent roles from lightweight ETF rotation roles to professional investment team roles.
- [x] Add investment committee style synthesis requirements.
- [x] Add ordinary-investor compliance, disclaimer, rating, action, sizing, and first-failure-condition requirements.
- [x] Update final writer system prompt.
- [x] Update prompt tests.
- [x] Run targeted unit tests.
- [x] Run syntax validation.

## Current Task: Make Reports More Detailed And Beginner-Friendly

- [x] Review the latest China ETF report output.
- [x] Confirm data fetching now has no source warnings.
- [x] Rename `Structured Evidence` to a technical appendix with an explanation.
- [x] Add a beginner reading guide to the Markdown report.
- [x] Make the candidate summary table more readable.
- [x] Replace US-market residual evidence text such as Nasdaq RSS and SEC companyfacts.
- [x] Translate default risk notes into Chinese.
- [x] Strengthen prompts for detailed beginner-friendly explanations and terminology definitions.
- [x] Update report and factor tests.
- [x] Run targeted unit tests.
- [x] Run syntax validation.
- [x] Run full unit tests.

## Next Technical Improvements

- [ ] Add explicit multi-round committee orchestrator instead of simulating debate inside the synthesis prompt.
- [ ] Add China ETF product metadata crawler for fund size, fee, tracking index, fund manager, listing date, and shares outstanding.
- [ ] Add Chinese news, announcement, and policy event sources for ETF themes.
- [ ] Add a second China ETF price provider fallback, such as Tencent or Sina, if Eastmoney is rate-limited.
- [ ] Add optional JSON report artifact for downstream automation.
- [ ] Add retry/backoff controls for public crawler sources.
- [ ] Add simple ETF rotation backtest after live report quality is stable.
