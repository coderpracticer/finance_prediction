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

## Current Task: Add News, Announcements, And ETF Product Data

- [x] Add ETF product metadata fields to the instrument schema.
- [x] Add news source and category fields to news items.
- [x] Add generic product detail fields to the fundamental snapshot.
- [x] Enrich the China ETF universe with asset type, exchange, category, tracking index, theme, and risk profile.
- [x] Add config-backed ETF product metadata as a stable source.
- [x] Add CNInfo announcement connector and parser.
- [x] Convert ETF product metadata into a Quality factor.
- [x] Add a news, announcement, and product-data analyst role.
- [x] Strengthen prompts to require clear but cautious investment advice.
- [x] Add parser, factor, and prompt tests.
- [x] Run targeted unit tests.
- [x] Run syntax validation.
- [x] Run full unit tests.
- [x] Smoke-test config loading with enriched ETF metadata.

## Next Technical Improvements

- [ ] Add explicit multi-round committee orchestrator instead of simulating debate inside the synthesis prompt.
- [ ] Add deeper China ETF product metadata crawler for live fund size, fee, fund manager, listing date, shares outstanding, premium/discount, and holdings.
- [ ] Add Chinese news and policy event sources for ETF themes beyond CNInfo announcements.
- [ ] Add a second China ETF price provider fallback, such as Tencent or Sina, if Eastmoney is rate-limited.
- [ ] Add optional JSON report artifact for downstream automation.
- [ ] Add retry/backoff controls for public crawler sources.
- [ ] Add simple ETF rotation backtest after live report quality is stable.
