import logging
import pandas as pd
import numpy as np
import ccxt.async_support as ccxt  # Using async support

logger = logging.getLogger("CryptoTechnicals")


class CryptoTechnicals:
    def __init__(self, exchange=None):
        """
        Initializes the Technical Indicator engine.
        Accepts an existing ccxt async exchange instance, or creates a default public Binance instance.
        """
        self.exchange = exchange
        self._owns_exchange = False
        if not self.exchange:
            self.exchange = ccxt.kraken({"enableRateLimit": True})
            self._owns_exchange = True

    async def close(self):
        if self._owns_exchange and self.exchange:
            await self.exchange.close()

    async def fetch_ohlcv_df(
        self, symbol: str, timeframe: str = "15m", limit: int = 100
    ):
        """Fetches OHLCV data and returns a pandas DataFrame."""
        try:
            # fetch_ohlcv returns: [ timestamp, open, high, low, close, volume ]
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            return None

    def compute_rsi(self, df: pd.DataFrame, window: int = 14) -> float:
        """Computes Relative Strength Index (RSI)."""
        if df is None or len(df) < window:
            return 50.0

        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])

    def compute_macd(
        self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
    ):
        """Computes Moving Average Convergence Divergence (MACD). Returns (macd_signal_str, macd_val, signal_val)."""
        if df is None or len(df) < slow + signal:
            return "NEUTRAL", 0.0, 0.0

        exp1 = df["close"].ewm(span=fast, adjust=False).mean()
        exp2 = df["close"].ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        sig = macd.ewm(span=signal, adjust=False).mean()

        current_macd = float(macd.iloc[-1])
        current_sig = float(sig.iloc[-1])

        if current_macd > current_sig:
            trend = "BULLISH"
        elif current_macd < current_sig:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"

        return trend, current_macd, current_sig

    def compute_bollinger_bands(
        self, df: pd.DataFrame, window: int = 20, num_std: int = 2
    ):
        """Computes Bollinger Bands and returns status relative to current price."""
        if df is None or len(df) < window:
            return "NORMAL"

        sma = df["close"].rolling(window=window).mean()
        std = df["close"].rolling(window=window).std()

        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)

        current_price = float(df["close"].iloc[-1])
        current_upper = float(upper_band.iloc[-1])
        current_lower = float(lower_band.iloc[-1])

        if current_price > current_upper:
            return "OVERBOUGHT_BB"
        elif current_price < current_lower:
            return "OVERSOLD_BB"
        else:
            return "NORMAL"

    def compute_atr(self, df: pd.DataFrame, window: int = 14) -> float:
        """Computes Average True Range (ATR) for dynamic volatility stop-loss calculation."""
        if df is None or len(df) < window + 1:
            return 0.0

        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=window).mean()
        return float(atr.iloc[-1])

    async def get_all_signals(self, symbol: str, timeframe: str = "15m") -> dict:
        """Fetches data and computes all technical indicators for the given symbol."""
        df = await self.fetch_ohlcv_df(symbol, timeframe=timeframe, limit=100)

        if df is None:
            return {
                "rsi": 50.0,
                "macd": "NEUTRAL",
                "bb": "NORMAL",
                "atr": 0.0,
                "atr_pct": 0.02,
                "error": "Failed to fetch OHLCV",
            }

        rsi = self.compute_rsi(df)
        macd_trend, macd_val, sig_val = self.compute_macd(df)
        bb = self.compute_bollinger_bands(df)
        atr = self.compute_atr(df)
        current_price = float(df["close"].iloc[-1])
        atr_pct = round(atr / current_price, 4) if current_price > 0 else 0.02

        return {
            "rsi": round(rsi, 2),
            "macd": macd_trend,
            "bb": bb,
            "atr": round(atr, 4),
            "atr_pct": atr_pct,
            "current_price": current_price,
        }


# For quick local testing
if __name__ == "__main__":
    import asyncio

    async def main():
        techs = CryptoTechnicals()
        signals = await techs.get_all_signals("SOL/USD", "15m")
        print(f"SOL/USD 15m Signals: {signals}")
        await techs.close()

    asyncio.run(main())
