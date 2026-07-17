from __future__ import annotations

import os
import sys
from typing import Any

from config import APP_CONFIG, MAX_SIGNALS_PER_SCAN, TIMEFRAMES
from core.scanner import SignalScanner
from notifications.telegram import TelegramBot
from services.history import add_history, is_new_signal, load_history, save_history
from services.position_state import calculate_position_from_state, load_position_state
from utils.logger import get_logger

logger = get_logger("main")


def main() -> None:
    logger.info("Starting SFP MSS scanner")
    scanner = SignalScanner()
    telegram = TelegramBot()
    history = load_history()

    try:
        telegram.poll_messages(limit=10)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Telegram polling failed: %s", exc)

    state = load_position_state("data/position_state.json")
    metrics = calculate_position_from_state(state)

    sent_count = 0
    for timeframe in APP_CONFIG.timeframes:
        try:
            signals = scanner.scan(timeframe)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Scanner failed for %s: %s", timeframe, exc)
            continue

        if not signals:
            logger.info("No valid signals for %s", timeframe)
            continue

        for signal in signals:
            if sent_count >= MAX_SIGNALS_PER_SCAN:
                break
            if not is_new_signal(signal.to_dict(), history):
                logger.info("Skipping duplicate signal for %s", signal.pair)
                continue
            logger.info("Signal found: %s", signal.pair)
            logger.info("TIMEFRAME: %s", signal.timeframe)
            logger.info("DIRECTION: %s", signal.direction)
            logger.info("SETUP: %s", signal.setup)
            logger.info("SCORE: %s/100", signal.confidence)
            logger.info("ENTRY: %.8f", signal.entry)
            logger.info("STOP: %.8f", signal.stop)
            logger.info("TARGET: %.8f", signal.target)
            logger.info("RR: %.2f:1", signal.rr)
            logger.info("POSITION STATE: balance=%s risk=%s size=%s", metrics.get("balance_usd"), metrics.get("risk_pct"), metrics.get("position_size_usd"))
            telegram.send_signal(signal.to_dict())
            history = add_history(signal.to_dict(), history)
            sent_count += 1

    save_history(history)
    logger.info("Scan complete. Signals sent: %s", sent_count)


if __name__ == "__main__":
    main()
