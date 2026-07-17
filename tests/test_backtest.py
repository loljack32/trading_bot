from core.models import Signal
from services.backtest import Backtester


def test_backtest_summary_builds_report():
    signal = Signal(
        pair="BTC-USDT-SWAP",
        exchange="OKX",
        timeframe="15m",
        direction="LONG",
        confidence=92,
        entry=100.0,
        stop=95.0,
        target=110.0,
        volume=1_000_000.0,
        setup="Liquidity sweep | Bullish SFP | Bullish MSS",
        score=92,
        filters=["HTF PASS", "EMA PASS"],
        rr=2.0,
    )
    backtester = Backtester()
    result = backtester.evaluate(
        signal,
        [
            {"high": 111.0, "low": 99.0},
            {"high": 109.0, "low": 97.0},
        ],
    )
    report = backtester.summarize([
        {**result, "timeframe": "15m", "pair": signal.pair, "direction": signal.direction, "entry": signal.entry, "stop": signal.stop, "target": signal.target, "rr": signal.rr}
    ])
    assert report.signals == 1
    assert report.winrate >= 0
    assert report.average_rr >= 0
    assert "15m" in report.by_timeframe
