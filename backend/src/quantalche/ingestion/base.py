from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from .models import OHLCBar, Timeframe


class OHLCClient(ABC):
    """Common interface every data-source client implements.

    Layer 2 modules should depend on this interface, not on a specific
    provider, so swapping Twelve Data/Binance for another source later
    doesn't ripple through the analysis engine.
    """

    source_name: str

    @abstractmethod
    def get_ohlc(
        self,
        symbol: str,
        timeframe: Timeframe,
        limit: int = 500,
        end_time: datetime | None = None,
        include_forming: bool = False,
    ) -> list[OHLCBar]:
        """Return OHLC bars, oldest first.

        By default the most recent bar returned is always a fully closed
        bar — never the still-forming current bar — per the project's
        non-repainting rule. The signal pipeline (analysis/aggregation/
        execution) must never be called with ``include_forming=True``.

        ``include_forming=True`` is an explicit opt-in for *display only*
        (a live-updating chart candle) -- it exists because a chart
        showing the currently-forming candle is legitimate and expected
        (that's what "live" means visually), it's only the *signal logic*
        that must never see it. Keeping this a separate, explicit flag
        rather than just always including it is what makes the
        non-repainting guarantee enforceable at the call site instead of
        relying on every caller remembering to drop the last bar.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Release any underlying HTTP resources. Override if needed."""
