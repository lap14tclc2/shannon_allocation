#!/usr/bin/env python3
"""Primary QPort Buy & Hold server entrypoint."""

import buyhold_server
from portfolio.automated_service import AutomatedPortfolioService

# Keep buyhold_server reusable while making the primary runtime use the
# dividend-aware service. _portfolio() resolves this global at request time.
buyhold_server.CorrectablePortfolioService = AutomatedPortfolioService

Handler = buyhold_server.Handler
main = buyhold_server.main

__all__ = ["Handler", "main"]


if __name__ == "__main__":
    main()
