from __future__ import annotations

import math

from backend.app.models.schemas import FactorScore, FundamentalSnapshot, InstrumentDataset, PriceBar


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
                f"Price rows={len(prices)}, news items={len(news)}, "
                f"SEC snapshot={'yes' if fundamentals is not None else 'no'}."
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
                    f"{lookback_days}-day return {raw_return:.2f}%; "
                    f"latest close {latest:.2f}, lookback close {lookback:.2f}."
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
                    f"Latest close is {distance:.2f}% from the {window}-day average "
                    f"({average:.2f})."
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
                evidence=f"Short available-history return {raw_return:.2f}%.",
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
                evidence="Not enough price history to estimate volatility or drawdown.",
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
                evidence=f"Annualized volatility over {len(sample)} daily returns is {volatility:.2f}%.",
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
                f"Maximum drawdown over {len(drawdown_window)} available price rows is "
                f"{max_drawdown:.2f}%."
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
                evidence=f"Downside annualized volatility is {downside_volatility:.2f}%.",
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
                evidence="Not enough volume history.",
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
            evidence=f"5-day average volume is {ratio:.2f}x the baseline window.",
        )
    ]


def _event_factors(news: list[object]) -> list[FactorScore]:
    count = len(news)
    score = clamp(35 + count * 4, 0, 100)
    confidence = 0.75 if count else 0.3
    return [
        FactorScore(
            name="news_attention",
            group="Event/Catalyst",
            score=score,
            confidence=confidence,
            raw_value=count,
            evidence=f"{count} recent Nasdaq RSS items were found.",
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
                evidence="No SEC companyfacts snapshot is available.",
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
            evidence=f"{coverage}/3 common SEC metrics are available.",
        )
    ]


def aggregate_score(factors: list[FactorScore]) -> tuple[float, float, str]:
    if not factors:
        return 0, 0, "weak"
    weighted = sum(factor.score * factor.confidence for factor in factors)
    confidence_sum = sum(factor.confidence for factor in factors)
    opportunity_score = weighted / confidence_sum if confidence_sum else 0
    confidence = confidence_sum / len(factors)
    if confidence >= 0.7:
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
