from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from config import HISTORY_FILE, HISTORY_MAX_AGE_HOURS


def load_history(path: str = HISTORY_FILE) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            history = json.load(handle)
            if not isinstance(history, list):
                return []
            return _prune_old_history(history)
    except (json.JSONDecodeError, OSError):
        return []


def save_history(history: list[dict[str, Any]], path: str = HISTORY_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    history = _prune_old_history(history)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=2, ensure_ascii=False)


def _prune_old_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if HISTORY_MAX_AGE_HOURS <= 0:
        return history
    cutoff = datetime.now(timezone.utc).timestamp() - HISTORY_MAX_AGE_HOURS * 3600
    pruned = [item for item in history if _parse_timestamp(item.get("time")) >= cutoff]
    return pruned


def _parse_timestamp(value: Any) -> float:
    if not isinstance(value, str):
        return 0.0
    try:
        dt = datetime.fromisoformat(value)
        return dt.timestamp()
    except ValueError:
        return 0.0


def is_new_signal(signal: dict[str, Any], history: list[dict[str, Any]]) -> bool:
    for item in history:
        if (
            item.get("pair") == signal.get("pair")
            and item.get("direction") == signal.get("direction")
            and item.get("timeframe") == signal.get("timeframe")
            and item.get("setup") == signal.get("setup")
        ):
            return False
    return True


def add_history(signal: dict[str, Any], history: list[dict[str, Any]], limit: int = 1000) -> list[dict[str, Any]]:
    item = dict(signal)
    item["time"] = datetime.now(timezone.utc).isoformat()
    history.append(item)
    return history[-limit:]
