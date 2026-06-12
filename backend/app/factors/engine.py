from __future__ import annotations

import math

from backend.app.models.schemas import FactorScore, FundamentalSnapshot, InstrumentDataset, NewsItem, PriceBar


def calculate_factors(dataset: InstrumentDataset) -> list[FactorScore]:
    factors: list[FactorScore] = []
    factors.extend(_data_coverage_factors(dataset.prices, dataset.news, dataset.fundamentals))
    factors.extend(_momentum_factors(dataset.prices))
    factors.extend(_risk_factors(dataset.prices))
    factors.extend(_volume_factors(dataset.prices))
    factors.extend(_event_factors(dataset.news))
    factors.extend(_fundamental_availability_factors(dataset.fundamentals))
    return factors


def _data_coverage_factors(
    prices: list[PriceBar],
    news: list[object],
    fundamentals: FundamentalSnapshot | None,
) -> list[FactorScore]:
    price_score = 90 if len(prices) >= 60 else 65 if len(prices) >= 20 else 20
    news_score = 80 if news else 35
    fundamentals_score = 75 if fundamentals is not None else 35
    score = price_score * 0.6 + news_score * 0.2 + fundamentals_score * 0.2
    return [
        FactorScore(
            name="evidence_coverage",
            group="Data Coverage",
            score=round(score, 1),
            confidence=0.9,
            raw_value=len(prices),
            evidence=(
                f"价格序列={len(prices)}条，新闻/公告线索={len(news)}条，"
                f"产品或基本面资料={'有' if fundamentals is not None else '暂无'}。"
            ),
        )
    ]


def _momentum_factors(prices: list[PriceBar]) -> list[FactorScore]:
    if len(prices) < 2:
        return [
            FactorScore(
                name="price_momentum",
                group="Momentum",
                score=25,
                confidence=0.8,
                evidence="Not enough price history.",
            )
        ]
    latest = prices[-1].close
    factors: list[FactorScore] = []
    for lookback_days, multiplier in ((5, 5.0), (20, 2.5), (60, 1.4)):
        if len(prices) <= lookback_days:
            continue
        lookback = prices[-lookback_days - 1].close
        raw_return = percentage_return(latest, lookback)
        score = clamp(50 + raw_return * multiplier, 0, 100)
        factors.append(
            FactorScore(
                name=f"return_{lookback_days}d",
                group="Momentum",
                score=score,
                confidence=0.85,
                raw_value=round(raw_return, 2),
                evidence=(
                    f"近{lookback_days}个交易日收益率 {raw_return:.2f}%；"
                    f"最新收盘价 {latest:.2f}，对比基准价 {lookback:.2f}。"
                ),
            )
        )
    for window in (20, 60):
        if len(prices) < window:
            continue
        average = sum(bar.close for bar in prices[-window:]) / window
        distance = percentage_return(latest, average)
        factors.append(
            FactorScore(
                name=f"ma_distance_{window}d",
                group="Momentum",
                score=clamp(50 + distance * 2.0, 0, 100),
                confidence=0.8,
                raw_value=round(distance, 2),
                evidence=(
                    f"最新收盘价相对{window}日均线偏离 {distance:.2f}%，"
                    f"{window}日均线为 {average:.2f}。"
                ),
            )
        )
    if not factors:
        lookback = prices[0].close
        raw_return = percentage_return(latest, lookback)
        factors.append(
            FactorScore(
                name="price_momentum",
                group="Momentum",
                score=clamp(50 + raw_return * 2, 0, 100),
                confidence=0.45,
                raw_value=round(raw_return, 2),
                evidence=f"可用短历史区间收益率 {raw_return:.2f}%。",
            )
        )
    return factors


def _risk_factors(prices: list[PriceBar]) -> list[FactorScore]:
    returns = daily_returns(prices)
    if len(returns) < 5:
        return [
            FactorScore(
                name="risk_data",
                group="Risk",
                score=25,
                confidence=0.75,
                evidence="价格历史不足，无法可靠估计波动率和最大回撤。",
            )
        ]
    factors: list[FactorScore] = []
    for window in (20, 60):
        if len(returns) < min(window, 10):
            continue
        sample = returns[-window:] if len(returns) >= window else returns
        volatility = sample_std(sample) * math.sqrt(252) * 100
        factors.append(
            FactorScore(
                name=f"volatility_{window}d",
                group="Risk",
                score=clamp(80 - volatility, 0, 100),
                confidence=0.75 if len(returns) >= window else 0.55,
                raw_value=round(volatility, 2),
                evidence=f"基于近{len(sample)}个日收益率估算的年化波动率为 {volatility:.2f}%。",
            )
        )
    drawdown_window = prices[-60:] if len(prices) >= 60 else prices
    max_drawdown = max_drawdown_pct(drawdown_window)
    factors.append(
        FactorScore(
            name="max_drawdown_60d",
            group="Risk",
            score=clamp(80 + max_drawdown * 2.0, 0, 100),
            confidence=0.75 if len(prices) >= 60 else 0.55,
            raw_value=round(max_drawdown, 2),
            evidence=(
                f"近{len(drawdown_window)}条可用价格记录中的最大回撤为 {max_drawdown:.2f}%。"
            ),
        )
    )
    downside = [item for item in returns[-60:] if item < 0]
    if downside:
        downside_volatility = sample_std(downside) * math.sqrt(252) * 100
        factors.append(
            FactorScore(
                name="downside_volatility",
                group="Risk",
                score=clamp(80 - downside_volatility, 0, 100),
                confidence=0.65,
                raw_value=round(downside_volatility, 2),
                evidence=f"只统计下跌日后的年化下行波动率为 {downside_volatility:.2f}%。",
            )
        )
    return factors


def _volume_factors(prices: list[PriceBar]) -> list[FactorScore]:
    volumes = [bar.volume for bar in prices if bar.volume is not None]
    if len(volumes) < 10:
        return [
            FactorScore(
                name="volume_attention",
                group="Volume/Attention",
                score=50,
                confidence=0.25,
                evidence="成交量历史不足，无法可靠判断近期关注度变化。",
            )
        ]
    recent = sum(volumes[-5:]) / min(5, len(volumes))
    baseline_window = volumes[-60:] if len(volumes) >= 60 else volumes
    baseline = sum(baseline_window) / len(baseline_window)
    ratio = recent / baseline if baseline else 1
    score = clamp(50 + (ratio - 1) * 35, 0, 100)
    return [
        FactorScore(
            name="volume_attention",
            group="Volume/Attention",
            score=score,
            confidence=0.8,
            raw_value=round(ratio, 3),
            evidence=f"近5日平均成交量为基准区间的 {ratio:.2f} 倍。",
        )
    ]


def _event_factors(news: list[NewsItem]) -> list[FactorScore]:
    count = len(news)
    score = clamp(35 + count * 4, 0, 100)
    confidence = 0.75 if count else 0.3
    titles = [item.title for item in news[:3] if item.title]
    if titles:
        evidence = f"发现{count}条近期新闻/公告线索，样例标题：" + " | ".join(titles)
    else:
        evidence = "当前未接入或未抓到可用的中文新闻、公告或政策线索。"
    return [
        FactorScore(
            name="news_attention",
            group="Event/Catalyst",
            score=score,
            confidence=confidence,
            raw_value=count,
            evidence=evidence,
        )
    ]


def _fundamental_availability_factors(
    fundamentals: FundamentalSnapshot | None,
) -> list[FactorScore]:
    if fundamentals is None:
        return [
            FactorScore(
                name="fundamental_coverage",
                group="Quality",
                score=35,
                confidence=0.25,
                evidence="当前未接入ETF规模、费率、跟踪指数、持仓或份额变化等产品资料。",
            )
        ]
    if fundamentals.details:
        detail_text = "；".join(
            f"{label_product_metric(key)}={value}"
            for key, value in fundamentals.details.items()
        )
        coverage = len(fundamentals.details)
        score = clamp(45 + coverage * 8, 45, 90)
        return [
            FactorScore(
                name="etf_product_profile",
                group="Quality",
                score=score,
                confidence=0.65,
                raw_value=coverage,
                evidence=f"已获得ETF产品资料：{detail_text}。",
            )
        ]
    coverage = sum(
        [fundamentals.has_revenue, fundamentals.has_net_income, fundamentals.has_eps]
    )
    score = 35 + coverage * 20
    return [
        FactorScore(
            name="fundamental_coverage",
            group="Quality",
            score=score,
            confidence=0.7,
            raw_value=coverage,
            evidence=f"已获得 {coverage}/3 项核心产品或基本面资料。",
        )
    ]


def label_product_metric(key: str) -> str:
    labels = {
        "asset_type": "资产类型",
        "exchange": "交易所",
        "category": "类别",
        "tracking_index": "跟踪指数",
        "fund_company": "基金公司",
        "theme": "主题",
        "risk_profile": "风险画像",
    }
    return labels.get(key, key)


def aggregate_score(factors: list[FactorScore]) -> tuple[float, float, str]:
    if not factors:
        return 0, 0, "weak"
    weighted = sum(factor.score * factor.confidence for factor in factors)
    confidence_sum = sum(factor.confidence for factor in factors)
    opportunity_score = weighted / confidence_sum if confidence_sum else 0
    confidence = confidence_sum / len(factors)
    coverage = next((factor for factor in factors if factor.name == "evidence_coverage"), None)
    if coverage is not None and coverage.score < 50:
        opportunity_score *= 0.75
        data_quality = "weak"
    elif confidence >= 0.7:
        data_quality = "good"
    elif confidence >= 0.45:
        data_quality = "mixed"
    else:
        data_quality = "weak"
    return round(opportunity_score, 2), round(confidence, 2), data_quality


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def percentage_return(latest: float, lookback: float) -> float:
    return (latest / lookback - 1) * 100 if lookback else 0


def daily_returns(prices: list[PriceBar]) -> list[float]:
    returns: list[float] = []
    for previous, current in zip(prices, prices[1:]):
        if previous.close:
            returns.append(current.close / previous.close - 1)
    return returns


def sample_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(max(variance, 0))


def max_drawdown_pct(prices: list[PriceBar]) -> float:
    peak = None
    worst = 0.0
    for bar in prices:
        peak = bar.close if peak is None else max(peak, bar.close)
        if peak:
            drawdown = (bar.close / peak - 1) * 100
            worst = min(worst, drawdown)
    return worst
