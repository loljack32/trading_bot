from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests

import config
from utils.helpers import safe_float
from utils.logger import get_logger


class OKXClient:
    def __init__(self) -> None:
        self.base_url = "https://www.okx.com"
        self.headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
        self.logger = get_logger("okx")

    def _sleep(self) -> None:
        if config.REQUEST_DELAY > 0:
            time.sleep(config.REQUEST_DELAY)

    def get_top_symbols(self) -> list[str]:
        url = f"{self.base_url}/api/v5/market/tickers"
        params = {"instType": "SWAP"}
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data.get("code") != "0":
                self.logger.warning("OKX tickers error: %s", data)
                return []

            markets: list[tuple[str, float]] = []
            for item in data.get("data", []):
                symbol = item.get("instId", "")
                if not symbol or not symbol.endswith(f"-{config.QUOTE_CURRENCY}-SWAP"):
                    continue

                state = item.get("state")
                if state not in {None, "", "live"}:
                    continue

                volume = safe_float(item.get("volCcy24h", item.get("vol24h", 0.0)))
                if volume <= 0:
                    continue

                markets.append((symbol, volume))

            markets.sort(key=lambda item: item[1], reverse=True)
            symbols = [item[0] for item in markets[: config.TOP_SYMBOLS_LIMIT]]
            self.logger.info("Loaded %s symbols from OKX", len(symbols))
            self._sleep()
            return symbols
        except requests.RequestException as exc:
            self.logger.warning("Symbol loading failed: %s", exc)
            return []

    def get_ohlcv(self, symbol: str, timeframe: str = "15m", limit: int = 200) -> pd.DataFrame | None:
        url = f"{self.base_url}/api/v5/market/candles"
        params = {"instId": symbol, "bar": timeframe, "limit": limit + 1}
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data.get("code") != "0":
                self.logger.warning("OHLCV error for %s: %s", symbol, data.get("msg"))
                return None

            rows = []
            for candle in data.get("data", []):
                rows.append([candle[0], candle[1], candle[2], candle[3], candle[4], candle[5]])
            if not rows:
                return None

            df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
            for column in ["open", "high", "low", "close", "volume"]:
                df[column] = pd.to_numeric(df[column], errors="coerce")
            df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms")
            df = df.sort_values("timestamp").reset_index(drop=True)
            if len(df) > 1:
                df = df.iloc[:-1]
            self._sleep()
            return df
        except requests.RequestException as exc:
            self.logger.warning("OHLCV fetch failed for %s: %s", symbol, exc)
            return None
