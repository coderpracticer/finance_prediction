from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Instrument:
    symbol: str
    name: str
    market: str = "US"
    stooq_symbol: str | None = None
    cik: str | None = None


@dataclass
class PriceBar:
    timestamp: int
    close: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None


@dataclass
class NewsItem:
    title: str
    link: str | None = None
    published_at: str | None = None
    summary: str | None = None


@dataclass
class FundamentalSnapshot:
    metric_count: int = 0
    available_metrics: list[str] = field(default_factory=list)
    has_revenue: bool = False
    has_net_income: bool = False
    has_eps: bool = False


@dataclass
class InstrumentDataset:
    instrument: Instrument
    prices: list[PriceBar] = field(default_factory=list)
    news: list[NewsItem] = field(default_factory=list)
    fundamentals: FundamentalSnapshot | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class FactorScore:
    name: str
    group: str
    score: float
    confidence: float
    evidence: str
    raw_value: float | int | str | None = None


@dataclass
class Candidate:
    symbol: str
    name: str
    market: str
    rank: int
    opportunity_score: float
    confidence: float
    data_quality: str
    factors: list[FactorScore]
    thesis: str
    risks: list[str]


@dataclass
class ScreeningResponse:
    run_id: str
    status: str
    candidates: list[Candidate]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
