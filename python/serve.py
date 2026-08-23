#!/usr/bin/env python3
"""Primary QPort Buy & Hold server entrypoint."""

from buyhold_server import Handler, main

__all__ = ["Handler", "main"]


if __name__ == "__main__":
    main()
