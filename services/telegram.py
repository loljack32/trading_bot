from __future__ import annotations

import requests

import config
from utils.logger import get_logger


class TelegramBot:
    def __init__(self) -> None:
        self.token = getattr(config, "TELEGRAM_TOKEN", "") or ""
        self.chat_id = getattr(config, "TELEGRAM_CHAT_ID", "") or ""
        self.logger = get_logger("telegram")

    def send(self, message: str) -> bool:
        if not self.token or not self.chat_id:
            self.logger.info("Telegram disabled: token or chat id missing")
            return False

        try:
            response = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            self.logger.warning("Telegram send failed: %s", exc)
            return False

    def send_signal(self, signal: dict[str, object]) -> bool:
        message = f"""
<b>⚡ SFP MSS SIGNAL</b>

<b>Pair:</b> {signal.get('pair')}
<b>Direction:</b> {signal.get('direction')}
<b>Confidence:</b> {signal.get('confidence')}%
<b>Entry:</b> {signal.get('entry')}
<b>Stop:</b> {signal.get('stop')}
<b>Target:</b> {signal.get('target')}
<b>RR:</b> {signal.get('rr')}:1
"""
        return self.send(message.strip())
