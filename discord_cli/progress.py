from __future__ import annotations

import datetime as _dt
from typing import Optional


class ProgressPrinter:
    """Utility to print formatted progress information to stdout."""

    def __init__(self) -> None:
        self._last_message: Optional[str] = None

    def _timestamp(self) -> str:
        return _dt.datetime.now().strftime("%H:%M:%S")

    def info(self, message: str) -> None:
        print(f"[{self._timestamp()}] {message}")
        self._last_message = message

    def debug(self, message: str) -> None:
        self.info(f"[DEBUG] {message}")

    def step(self, message: str) -> None:
        self.info(f"➡️  {message}")

    def success(self, message: str) -> None:
        self.info(f"✅ {message}")

    def warning(self, message: str) -> None:
        self.info(f"⚠️  {message}")

    def error(self, message: str) -> None:
        self.info(f"❌ {message}")

    def divider(self) -> None:
        print("-" * 60)
