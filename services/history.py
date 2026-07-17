from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from config import HISTORY_FILE


def load_history(path: str = HISTORY_FILE) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return []


def save_history(history: list[dict[str, Any]], path: str = HISTORY_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=2, ensure_ascii=False)


def is_new_signal(signal: dict[str, Any], history: list[dict[str, Any]]) -> bool:
    for item in history:
        if (
            item.get("pair") == signal.get("pair")
            and item.get("direction") == signal.get("direction")
            and item.get("timeframe") == signal.get("timeframe")
        ):
            return False
    return True


def add_history(signal: dict[str, Any], history: list[dict[str, Any]], limit: int = 1000) -> list[dict[str, Any]]:
    item = dict(signal)
    item["time"] = datetime.now(timezone.utc).isoformat()
    history.append(item)
    return history[-limit:]
