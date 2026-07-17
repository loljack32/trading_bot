from pathlib import Path

from services.position_state import calculate_position_from_state, load_position_state, update_position_state_from_command


def test_worker_commands_update_balance_and_risk(tmp_path: Path) -> None:
    state_path = tmp_path / "worker_state.json"

    state = load_position_state(state_path)
    assert state["balance_usd"] is None
    assert state["risk_pct"] is None

    state = update_position_state_from_command("/balance 2000", state_path)
    assert state["balance_usd"] == 2000.0

    state = update_position_state_from_command("/procent 10", state_path)
    assert state["risk_pct"] == 10.0

    metrics = calculate_position_from_state(state)
    assert metrics["risk_amount_usd"] == 200.0
    assert metrics["position_size_usd"] == 2000.0
