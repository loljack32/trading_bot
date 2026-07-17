from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.logger import get_logger


logger = get_logger("position_state")


DEFAULT_STATE = {
    "balance_usd": None,
    "risk_pct": None,
    "last_updated": None,
}


def load_position_state(path: str | Path | None = None) -> dict[str, Any]:
    state_path = Path(path or "data/position_state.json")
    if not state_path.exists():
        return dict(DEFAULT_STATE)

    try:
        with state_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        logger.warning("Failed to load position state %s: %s", state_path, exc)
        return dict(DEFAULT_STATE)

    if not isinstance(data, dict):
        logger.warning("Position state content invalid (not dict): %s", state_path)
        return dict(DEFAULT_STATE)

    state = dict(DEFAULT_STATE)
    state.update(data)
    return state


def save_position_state(state: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    state_path = Path(path or "data/position_state.json")
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure last_updated is set to now if not provided
    if not state.get("last_updated"):
        state["last_updated"] = datetime.utcnow().isoformat()

    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(state_path.parent))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, str(state_path))
        logger.info("Position state saved to %s (size=%s bytes)", state_path, state_path.stat().st_size)
    except Exception as exc:
        logger.exception("Failed to save position state to %s: %s", state_path, exc)
        # Cleanup temp file if exists
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        raise

    return state


def update_position_state_from_command(command: str, path: str | Path | None = None) -> dict[str, Any]:
    state = load_position_state(path)
    original = dict(state)
    text = (command or "").strip()

    if text.startswith("/balance"):
        parts = text.split()
        if len(parts) >= 2:
            try:
                balance = float(parts[1])
            except Exception:
                balance = None
            if balance is not None and balance > 0:
                state["balance_usd"] = balance
            else:
                logger.warning("Ignored invalid balance command value: %s", parts[1] if len(parts) >= 2 else None)

    if text.startswith("/procent"):
        parts = text.split()
        if len(parts) >= 2:
            try:
                risk_pct = float(parts[1])
            except Exception:
                risk_pct = None
            if risk_pct is not None and risk_pct > 0:
                state["risk_pct"] = risk_pct
            else:
                logger.warning("Ignored invalid risk command value: %s", parts[1] if len(parts) >= 2 else None)

    # Only update last_updated if there's an actual change
    if state != original:
        state["last_updated"] = datetime.utcnow().isoformat()
        saved = save_position_state(state, path)
        logger.info("Position state updated by command '%s': %s -> %s", text, original, saved)
        return saved

    logger.info("No changes applied for command: %s", text)
    return state


def calculate_position_from_state(state: dict[str, Any]) -> dict[str, Any]:
    balance = state.get("balance_usd")
    risk_pct = state.get("risk_pct")

    if balance is None or risk_pct is None:
        return {
            "balance_usd": balance,
            "risk_pct": risk_pct,
            "risk_amount_usd": None,
            "position_size_usd": None,
            "leverage": None,
        }

    risk_amount = float(balance) * (float(risk_pct) / 100.0)
    leverage = 10.0
    position_size = risk_amount * leverage

    return {
        "balance_usd": balance,
        "risk_pct": risk_pct,
        "risk_amount_usd": round(risk_amount, 2),
        "position_size_usd": round(position_size, 2),
        "leverage": leverage,
    }
