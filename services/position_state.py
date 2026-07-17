from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
    except Exception:
        return dict(DEFAULT_STATE)

    if not isinstance(data, dict):
        return dict(DEFAULT_STATE)

    state = dict(DEFAULT_STATE)
    state.update(data)
    return state


def save_position_state(state: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    state_path = Path(path or "data/position_state.json")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    return state


def update_position_state_from_command(command: str, path: str | Path | None = None) -> dict[str, Any]:
    state = load_position_state(path)
    text = (command or "").strip()

    if text.startswith("/balance"):
        parts = text.split()
        if len(parts) >= 2:
            try:
                balance = float(parts[1])
            except ValueError:
                balance = None
            if balance is not None and balance > 0:
                state["balance_usd"] = balance

    if text.startswith("/procent"):
        parts = text.split()
        if len(parts) >= 2:
            try:
                risk_pct = float(parts[1])
            except ValueError:
                risk_pct = None
            if risk_pct is not None and risk_pct > 0:
                state["risk_pct"] = risk_pct

    state["last_updated"] = str(Path(path or "data/position_state.json").stat().st_mtime_ns) if Path(path or "data/position_state.json").exists() else None
    return save_position_state(state, path)


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
