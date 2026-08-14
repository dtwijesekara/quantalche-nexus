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
    ) -> list[OHLCBar]:
        """Return closed OHLC bars, oldest first.

        The most recent bar returned must be a fully closed bar — never the
        still-forming current bar — per the project's non-repainting rule.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Release any underlying HTTP resources. Override if needed."""
