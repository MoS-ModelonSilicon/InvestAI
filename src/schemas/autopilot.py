from pydantic import BaseModel
from typing import Optional


class SleeveSummary(BaseModel):
    label: str
    pct: float
    symbols: list[str]


class ProfileOut(BaseModel):
    id: str
    name: str
    subtitle: str
    risk_level: str
    risk_score: int
    description: str
    strategy: str
    rebalance: str
    expected_return: str
    expected_drawdown: str
    sleeves: list[SleeveSummary]


class HoldingDetail(BaseModel):
    symbol: str
    sleeve: str
    allocation_pct: float
    shares: float
    buy_price: float
    invested: float
    current_price: float
    current_value: float
    gain_loss: float
    gain_loss_pct: float


class SleeveResult(BaseModel):
    label: str
    invested: float
    current_value: float
    gain_loss: float
    pct: float


class SimulationStats(BaseModel):
    total_return: float
    total_return_pct: float
    bench_return_pct: float
    alpha: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    best_day: float
    worst_day: float
    final_value: float
    starting_amount: float
    trading_days: int


class ChartData(BaseModel):
    dates: list[str]
    portfolio: list[float]
    benchmark: list[float]


class ProfileBrief(BaseModel):
    id: str
    name: str
    subtitle: str
    strategy: str
    risk_level: str


class SimulationResult(BaseModel):
    profile: ProfileBrief
    chart: ChartData
    stats: SimulationStats
    holdings: list[HoldingDetail]
    sleeves: list[SleeveResult]
    cash: float
