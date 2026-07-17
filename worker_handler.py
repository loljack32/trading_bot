from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from services.position_state import load_position_state, save_position_state, update_position_state_from_command


def handle_worker_request(payload: dict[str, Any], repo_root: str | None = None) -> dict[str, Any]:
    repo_root_path = Path(repo_root or os.getcwd())
    state_path = repo_root_path / "data" / "position_state.json"

    text = payload.get("text") or ""
    if isinstance(text, str) and text:
        if text.startswith("/balance") or text.startswith("/procent"):
            update_position_state_from_command(text, state_path)

    state = load_position_state(state_path)
    return {
        "ok": True,
        "state": state,
    }


if __name__ == "__main__":
    print(handle_worker_request({"text": "/balance 2500"}))
