#!/usr/bin/env python3
"""Primary QPort server entrypoint.

The operational product is the buy-and-hold portfolio information system.
Legacy optimizer/backtest HTTP behavior lives in `research_legacy_server.py` and
is exposed only through the Research boundary by `buyhold_server.Handler`.
"""

from buyhold_server import Handler, main
from research_legacy_server import (
    MAX_ALLOCATIONS,
    MAX_FIXED_SYMBOLS,
    MIN_ALLOCATIONS,
    MIN_FIXED_SYMBOLS,
    VALID_UNIVERSES,
    _normalise_symbols,
)

__all__ = [
    "Handler",
    "main",
    "MIN_FIXED_SYMBOLS",
    "MAX_FIXED_SYMBOLS",
    "MIN_ALLOCATIONS",
    "MAX_ALLOCATIONS",
    "VALID_UNIVERSES",
    "_normalise_symbols",
]


if __name__ == "__main__":
    main()
