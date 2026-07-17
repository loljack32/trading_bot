from __future__ import annotations

import requests

import config
from services.position_state import calculate_position_from_state, load_position_state, save_position_state, update_position_state_from_command
from utils.logger import get_logger


class TelegramBot:
    def __init__(self) -> None:
        self.token = getattr(config, "TELEGRAM_TOKEN", "") or ""
        self.chat_id = getattr(config, "TELEGRAM_CHAT_ID", "") or ""
        self.logger = get_logger("telegram")
        self._last_update_id: int | None = None

    def send(self, message: str, chat_id: str | None = None) -> bool:
        target_chat_id = chat_id or self.chat_id
        if not self.token or not target_chat_id:
            self.logger.info("Telegram disabled: token or chat id missing")
            return False

        try:
            response = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": target_chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
            response.raise_for_status()
            self.logger.info("Telegram message sent to %s (len=%s)", target_chat_id, len(message))
            return True
        except requests.RequestException as exc:
            self.logger.warning("Telegram send failed: %s; response=%s", exc, getattr(exc, 'response', None))
            return False

    def send_signal(self, signal: dict[str, object]) -> bool:
        state = load_position_state(config.POSITION_STATE_FILE if hasattr(config, "POSITION_STATE_FILE") else "data/position_state.json")
        metrics = calculate_position_from_state(state)
        message = f"""
<b>⚡ SFP MSS SIGNAL</b>

<b>Pair:</b> {signal.get('pair')}
<b>Direction:</b> {signal.get('direction')}
<b>Confidence:</b> {signal.get('confidence')}%
<b>Setup:</b> {signal.get('setup')}
<b>Entry:</b> {signal.get('entry')}
<b>Stop:</b> {signal.get('stop')}
<b>Target:</b> {signal.get('target')}
<b>RR:</b> {signal.get('rr')}:1
<b>Balance:</b> ${metrics['balance_usd'] if metrics['balance_usd'] is not None else 'n/a'}
<b>Risk:</b> {metrics['risk_pct'] if metrics['risk_pct'] is not None else 'n/a'}%
<b>Risk amount:</b> ${metrics['risk_amount_usd'] if metrics['risk_amount_usd'] is not None else 'n/a'}
<b>Position size:</b> ${metrics['position_size_usd'] if metrics['position_size_usd'] is not None else 'n/a'}
"""
        return self.send(message.strip())

    def handle_message(self, message: str, chat_id: str | None = None) -> bool:
        text = (message or "").strip()
        if not text:
            return False
        self.logger.info("Received Telegram message from %s: %s", chat_id or "unknown", text)

        if text.startswith("/balance") or text.startswith("/procent"):
            path = getattr(config, "POSITION_STATE_FILE", "data/position_state.json")
            if text.startswith("/balance"):
                state = update_position_state_from_command(text, path)
                if state.get("balance_usd") is not None:
                    self.send(f"✅ Balance saved: ${state.get('balance_usd')}", chat_id)
                else:
                    self.send("❌ Invalid balance value", chat_id)
                return True

            if text.startswith("/procent"):
                state = update_position_state_from_command(text, path)
                if state.get("risk_pct") is not None:
                    self.send(f"✅ Risk saved: {state.get('risk_pct')}%", chat_id)
                else:
                    self.send("❌ Invalid risk value", chat_id)
                return True

        self.send("Available commands:\n/balance <amount_usd>\n/procent <risk_pct>", chat_id)
        return False

    def sync_worker_state(self) -> dict[str, object]:
        path = getattr(config, "POSITION_STATE_FILE", "data/position_state.json")
        state = load_position_state(path)
        save_position_state(state, path)
        return state

    def poll_messages(self, limit: int = 10) -> int:
        if not self.token:
            return 0

        params = {"timeout": 5, "limit": limit}
        if self._last_update_id is not None:
            params["offset"] = self._last_update_id + 1

        try:
            response = requests.get(
                f"https://api.telegram.org/bot{self.token}/getUpdates",
                params=params,
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            self.logger.warning("Telegram poll failed: %s", exc)
            return 0

        updates = response.json().get("result", [])
        handled = 0
        for update in updates:
            update_id = update.get("update_id")
            message = update.get("message") or {}
            text = message.get("text") or ""
            chat_obj = message.get("chat") or {}
            chat_id = str(chat_obj.get("id")) if chat_obj.get("id") is not None else None
            if not text:
                continue
            self.handle_message(text, chat_id)
            handled += 1
            if update_id is not None:
                self._last_update_id = max(self._last_update_id or update_id, update_id)
        return handled
