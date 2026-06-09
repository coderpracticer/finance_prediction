from __future__ import annotations

from backend.app.models.schemas import FactorScore, FundamentalSnapshot, InstrumentDataset, PriceBar


def calculate_factors(dataset: InstrumentDataset) -> list[FactorScore]:
    factors: list[FactorScore] = []
    factors.extend(_momentum_factors(dataset.prices))
    factors.extend(_volume_factors(dataset.prices))
    factors.extend(_event_factors(dataset.news))
    factors.extend(_fundamental_availability_factors(dataset.fundamentals))
    return factors


def _momentum_factors(prices: list[PriceBar]) -> list[FactorScore]:
    if len(prices) < 2:
        return [
            FactorScore(
                name="price_momentum",
                group="Momentum",
                score=50,
                confidence=0.2,
                evidence="Not enough price history.",
            )
        ]
    latest = prices[-1].close
    lookback = prices[-21].close if len(prices) >= 21 else prices[0].close
    raw_return = (latest / lookback - 1) * 100 if lookback else 0
    score = clamp(50 + raw_return * 2, 0, 100)
    return [
        FactorScore(
            name="price_momentum",
            group="Momentum",
            score=score,
            confidence=0.85 if len(prices) >= 21 else 0.55,
            raw_value=round(raw_return, 2),
            evidence=f"Latest close {latest:.2f}; lookback close {lookback:.2f}.",
        )
    ]


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

