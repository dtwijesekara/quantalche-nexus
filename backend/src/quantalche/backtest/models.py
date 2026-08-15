from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ..execution.models import TradeDirection


class ModuleAccuracyStat(BaseModel):
    module: str
    scored_signals: int
    correct: int
    incorrect: int
    accuracy: float | None  # None if scored_signals == 0


class TradeRecord(BaseModel):
    direction: TradeDirection
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence: float
    signal_time: datetime
    fill_time: datetime | None = None
    exit_time: datetime | None = None
    outcome: str = "open"  # "tp_hit" | "stopped_out" | "expired" | "open"


class SegmentReport(BaseModel):
    label: str
    start_time: datetime | None
    end_time: datetime | None
    bar_count: int
    trades: list[TradeRecord]
    total_signals: int
    filled: int
    resolved: int
    wins: int
    losses: int
    win_rate: float | None
    expectancy_r: float | None
    module_accuracy: list[ModuleAccuracyStat]


class BacktestReport(BaseModel):
    label: str
    overall: SegmentReport
    walk_forward_segments: list[SegmentReport]
