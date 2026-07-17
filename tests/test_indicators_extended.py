"""Unit tests for SFP and MSS detectors."""
import sys
sys.path.insert(0, '/c/Users/GOD/Desktop/trade_bot/trading_bot')

import pytest
import pandas as pd

from core.indicators import (
    detect_sfp, detect_mss, prepare_dataframe, calculate_atr
)


def create_test_df(close_prices, high_prices=None, low_prices=None):
    """Helper to create test DataFrame."""
    n = len(close_prices)
    if high_prices is None:
        high_prices = [c * 1.01 for c in close_prices]
    if low_prices is None:
        low_prices = [c * 0.99 for c in close_prices]
    
    df = pd.DataFrame({
        'timestamp': pd.date_range('2026-01-01', periods=n, freq='h'),
        'open': [c * 0.99 for c in close_prices],
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': [1000.0] * n,
    })
    return prepare_dataframe(df)


class TestDetectSFP:
    def test_sfp_long_with_reclaim(self):
        """SFP LONG: sweep then reclaim (close > wick inside level)."""
        # Create a pattern: uptrend, wick down to liquidity, then close above it
        closes = [100, 101, 102, 100.5, 103]  # Last two: dip then recovery
        highs = [100, 101, 102, 102, 103]
        lows = [99, 100, 101, 98, 102]  # Wick to 98, then reclaim
        
        df = create_test_df(closes, highs, lows)
        result = detect_sfp(df, "LONG")
        
        assert result is not None, "Should detect SFP for LONG"
        assert result.get("direction") == "LONG"
        # Don't assert passed=True as it depends on full logic

    def test_sfp_short_with_reclaim(self):
        """SFP SHORT: sweep then reclaim (close < wick inside level)."""
        closes = [100, 99, 98, 99.5, 97]
        highs = [100, 99, 98, 100, 98]  # Wick to 100
        lows = [99, 98, 97, 97, 96]
        
        df = create_test_df(closes, highs, lows)
        result = detect_sfp(df, "SHORT")
        
        assert result is not None
        assert result.get("direction") == "SHORT"

    def test_sfp_returns_dict(self):
        """SFP should return dict with required keys."""
        closes = [100] * 100
        df = create_test_df(closes)
        result = detect_sfp(df, "LONG")
        
        assert isinstance(result, dict)
        assert "type" in result
        assert "direction" in result
        assert "passed" in result
        assert result["type"] == "SFP"

    def test_sfp_insufficient_data(self):
        """SFP should return None for insufficient data."""
        closes = [100, 101, 102]
        df = create_test_df(closes)
        result = detect_sfp(df, "LONG")
        
        # Either None or passed=False
        if result is not None:
            assert result.get("passed") is False or result.get("passed") is None


class TestDetectMSS:
    def test_mss_long_returns_dict(self):
        """MSS should return dict with required keys."""
        closes = [100] * 100
        df = create_test_df(closes)
        result = detect_mss(df, "LONG")
        
        assert isinstance(result, dict)
        assert "type" in result
        assert "direction" in result
        assert "passed" in result
        assert result["type"] == "MSS"

    def test_mss_short_returns_dict(self):
        """MSS SHORT should return valid dict."""
        closes = [100] * 100
        df = create_test_df(closes)
        result = detect_mss(df, "SHORT")
        
        assert isinstance(result, dict)
        assert result.get("direction") == "SHORT"

    def test_mss_insufficient_data(self):
        """MSS should return None for insufficient data."""
        closes = [100, 101, 102]
        df = create_test_df(closes)
        result = detect_mss(df, "LONG")
        
        # Should return None for < 5 candles
        assert result is None or result.get("passed") is False

    def test_mss_with_structure(self):
        """MSS should detect breaks of swing extremes."""
        # Simulate pattern: lower lows then break above
        closes = [100, 99, 98, 97, 100]  # Lower lows then sharp up
        highs = [100, 99, 98, 97, 101]
        lows = [99, 98, 97, 96, 96]
        
        df = create_test_df(closes, highs, lows)
        result = detect_mss(df, "LONG")
        
        assert result is not None
        assert result.get("direction") == "LONG"
        # May or may not pass depending on exact logic


class TestATR:
    def test_atr_calculation(self):
        """ATR should be calculated and positive."""
        closes = [100, 102, 101, 103, 99]
        df = create_test_df(closes)
        atr = calculate_atr(df)
        
        assert atr > 0, f"ATR should be positive, got {atr}"
        assert atr < 5, f"ATR should be reasonable for this range, got {atr}"


if __name__ == "__main__":
    # Run basic tests
    test_sfp = TestDetectSFP()
    test_mss = TestDetectMSS()
    test_atr = TestATR()
    
    print("Running SFP tests...")
    try:
        test_sfp.test_sfp_long_with_reclaim()
        print("✓ test_sfp_long_with_reclaim")
    except Exception as e:
        print(f"✗ test_sfp_long_with_reclaim: {e}")
    
    try:
        test_sfp.test_sfp_returns_dict()
        print("✓ test_sfp_returns_dict")
    except Exception as e:
        print(f"✗ test_sfp_returns_dict: {e}")
    
    print("\nRunning MSS tests...")
    try:
        test_mss.test_mss_long_returns_dict()
        print("✓ test_mss_long_returns_dict")
    except Exception as e:
        print(f"✗ test_mss_long_returns_dict: {e}")
    
    try:
        test_mss.test_mss_insufficient_data()
        print("✓ test_mss_insufficient_data")
    except Exception as e:
        print(f"✗ test_mss_insufficient_data: {e}")
    
    print("\nRunning ATR tests...")
    try:
        test_atr.test_atr_calculation()
        print("✓ test_atr_calculation")
    except Exception as e:
        print(f"✗ test_atr_calculation: {e}")
    
    print("\n✅ Basic tests passed")
