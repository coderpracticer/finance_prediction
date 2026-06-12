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

## Next Technical Improvements

- [ ] Add a second China ETF price provider fallback, such as Tencent or Sina, if Eastmoney is rate-limited.
- [ ] Add ETF metadata crawler for fund size, tracking index, fee, and listing date.
- [ ] Add optional JSON report artifact for downstream automation.
- [ ] Add retry/backoff controls for public crawler sources.
- [ ] Add simple ETF rotation backtest after live report quality is stable.
