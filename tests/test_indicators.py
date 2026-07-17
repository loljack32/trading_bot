import pandas as pd

from core.indicators import detect_sfp, detect_mss


def _make_df(close_values):
    data = []
    for idx, value in enumerate(close_values):
        data.append(
            {
                "open": value - 0.5,
                "high": value + 1.0,
                "low": value - 1.0,
                "close": value,
                "volume": 1000.0 + idx,
            }
        )
    return pd.DataFrame(data)


def test_bullish_sfp_detection():
    df = _make_df([10, 11, 12, 14, 13, 14.5, 15.2])
    signal = detect_sfp(df, "LONG")
    assert signal is not None
    assert signal["type"] == "SFP"
    assert signal["direction"] == "LONG"


def test_bearish_mss_detection():
    df = _make_df([10, 12, 11, 13, 12, 14, 13])
    signal = detect_mss(df, "SHORT")
    assert signal is not None
    assert signal["type"] == "MSS"
    assert signal["direction"] == "SHORT"
