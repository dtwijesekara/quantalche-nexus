from __future__ import annotations

from abc import ABC, abstractmethod

from ..ingestion.models import OHLCBar
from .models import ModuleSignal


class AnalysisModule(ABC):
    """Shared contract for every Layer 2 module.

    Modules stay fully independent -- no shared state, no cross-talk
    (architecture.md Layer 2). Each one is validated against the source
    material on its own before being wired into anything else.
    """

    name: str

    @abstractmethod
    def evaluate(self, bars: list[OHLCBar]) -> ModuleSignal:
        """``bars`` must be ordered oldest -> newest, closed bars only
        (non-repainting). Returns this module's current bias + confidence
        given everything in ``bars``.

        Call this repeatedly with a growing bar list for a non-repainting
        backtest replay (Layer 7), or once with the latest live bars for a
        live signal request -- the module itself doesn't care which.
        """
        raise NotImplementedError
