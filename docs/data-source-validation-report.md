# 数据源验证报告

生成时间：2026-06-09T03:02:43+00:00

## Summary

- passed: 8
- partial: 0
- weak: 0
- failed: 0
- skipped: 1

## Results

| Source | Category | Status | Latency | Records | Fields | Warnings | Errors |
| --- | --- | --- | --- | --- | --- | --- | --- |
| yahoo_chart_prices | price | passed | 1617 ms | 64 | timestamp, close, high, low, open, volume | - | - |
| sec_companyfacts | fundamentals | passed | 11647 ms | 503 | AccountsPayable, AccountsPayableCurrent, AccountsReceivableNetCurrent, AccruedIncomeTaxesCurrent, AccruedIncomeTaxesNoncurrent, AccruedLiabilities, AccruedLiabilitiesCurrent, AccruedMarketingCostsCurrent, ... | - | - |
| nasdaq_stock_rss | news | passed | 1898 ms | 15 | title, link, pubDate, description | - | - |
| yahoo_chart_prices | price | passed | 1492 ms | 64 | timestamp, close, high, low, open, volume | - | - |
| sec_companyfacts | fundamentals | passed | 11033 ms | 544 | AccountsPayableCurrent, AccountsReceivableNet, AccountsReceivableNetCurrent, AccountsReceivableNetNoncurrent, AccruedIncomeTaxesCurrent, AccruedIncomeTaxesNoncurrent, AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment, AccumulatedOtherComprehensiveIncomeLossAvailableForSaleSecuritiesAdjustmentNetOfTax, ... | - | - |
| nasdaq_stock_rss | news | passed | 1430 ms | 15 | title, link, pubDate, description | - | - |
| yahoo_chart_prices | price | passed | 1268 ms | 64 | timestamp, close, high, low, open, volume | - | - |
| sec_companyfacts | fundamentals | skipped | - | 0 | - | Skipped because SPY does not have a CIK. | - |
| nasdaq_stock_rss | news | passed | 1306 ms | 15 | title, link, pubDate, description | - | - |

## Interpretation

- `passed` 表示该源连通、解析成功且返回了记录。
- `partial` 表示可用但存在字段缺失或质量警告。
- `weak` 表示连通但没有有效记录。
- `failed` 表示连通或解析失败。
- `skipped` 表示缺少 API key、CIK 或配置未启用。

## Next Checks

1. 对 passed/partial 的数据源扩大 universe 验证。
2. 对 failed 的数据源确认是否是网络、限流、User-Agent 或 endpoint 变化。
3. 决定 Phase 1 的首选 price、fundamentals、news 数据源组合。
