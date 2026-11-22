"""AI-BS Sovereign Quantitative Crypto Strategy Backtesting Sandbox.

Specifically models algorithmic execution around the critical support baseline ($0.05719).

Governance & Safety Standard:
Strict Zero-Mock Real Money Rule (AGENTS.md):
- All simulations are explicitly segregated from live accounting/tax tables.
- All records are labeled with execution_mode='STRATEGY_SIMULATION_BACKTEST_ONLY'.
- Never commits synthetic transactions to live production ledgers.
"""

from __future__ import annotations

import math
import os
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

_WORKSPACE_ROOT = Path("C:/AI-BS") if Path("C:/AI-BS").exists() else Path(__file__).resolve().parent.parent.parent
_DB_PATH = _WORKSPACE_ROOT / "database" / "crypto_backtest_sandbox.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class BacktestTrade:
    trade_id: str
    timestamp: float
    trade_type: str  # BUY, SELL
    price: float
    quantity: float
    usd_value: float
    fee_usd: float
    realized_pnl_usd: float


@dataclass
class BacktestSummary:
    strategy_name: str
    symbol: str
    initial_capital_usd: float
    final_capital_usd: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    win_rate_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    support_level_tested: float
    execution_mode: str = "STRATEGY_SIMULATION_BACKTEST_ONLY"


class CryptoBacktestSandbox:
    """Quantitative backtesting engine for high-frequency trading rules."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or _DB_PATH
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS backtest_runs (
                        run_id TEXT PRIMARY KEY,
                        strategy_name TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        initial_capital_usd REAL,
                        final_capital_usd REAL,
                        total_return_pct REAL,
                        total_trades INTEGER,
                        win_rate_pct REAL,
                        max_drawdown_pct REAL,
                        sharpe_ratio REAL,
                        support_level_tested REAL,
                        created_at REAL,
                        execution_mode TEXT DEFAULT 'STRATEGY_SIMULATION_BACKTEST_ONLY'
                    )
                """)
        finally:
            conn.close()

    def run_support_bounce_strategy(
        self,
        price_series: List[float],
        support_level: float = 0.05719,
        initial_capital: float = 1000.0,
        trade_allocation_pct: float = 0.25,
        take_profit_pct: float = 0.035,
        stop_loss_pct: float = 0.020,
        fee_rate: float = 0.001,  # 0.10% maker/taker
    ) -> BacktestSummary:
        """
        Executes a deterministic support-bounce backtest:
        - Buys when price dips to within 0.5% of or below support_level ($0.05719).
        - Takes profit at +3.5% above entry.
        - Cuts loss at -2.0% below entry.
        """
        cash = initial_capital
        holdings = 0.0
        entry_price = 0.0
        trades: List[BacktestTrade] = []
        equity_curve: List[float] = [initial_capital]
        winning_trades = 0

        for idx, price in enumerate(price_series):
            # Check Exit Conditions if holding
            if holdings > 0.0:
                pnl_pct = (price - entry_price) / entry_price
                if pnl_pct >= take_profit_pct or pnl_pct <= -stop_loss_pct or idx == len(price_series) - 1:
                    # Sell
                    gross_proceeds = holdings * price
                    fee = gross_proceeds * fee_rate
                    net_proceeds = gross_proceeds - fee
                    pnl_usd = net_proceeds - (holdings * entry_price)

                    cash += net_proceeds
                    if pnl_usd > 0:
                        winning_trades += 1

                    trades.append(BacktestTrade(
                        trade_id=f"trade_sell_{idx}",
                        timestamp=float(idx),
                        trade_type="SELL",
                        price=price,
                        quantity=holdings,
                        usd_value=gross_proceeds,
                        fee_usd=fee,
                        realized_pnl_usd=round(pnl_usd, 4),
                    ))
                    holdings = 0.0
                    entry_price = 0.0

            # Check Buy Condition if cash available and price tests support
            elif holdings == 0.0 and price <= (support_level * 1.005):
                buy_budget = cash * trade_allocation_pct
                if buy_budget > 10.0:
                    fee = buy_budget * fee_rate
                    net_investment = buy_budget - fee
                    holdings = net_investment / price
                    cash -= buy_budget
                    entry_price = price

                    trades.append(BacktestTrade(
                        trade_id=f"trade_buy_{idx}",
                        timestamp=float(idx),
                        trade_type="BUY",
                        price=price,
                        quantity=holdings,
                        usd_value=buy_budget,
                        fee_usd=fee,
                        realized_pnl_usd=0.0,
                    ))

            # Mark to market equity
            current_equity = cash + (holdings * price)
            equity_curve.append(current_equity)

        # Performance Metrics
        final_capital = equity_curve[-1]
        total_return_pct = round(((final_capital - initial_capital) / initial_capital) * 100, 2)
        total_closed_trades = len([t for t in trades if t.trade_type == "SELL"])
        win_rate = round((winning_trades / total_closed_trades * 100), 1) if total_closed_trades > 0 else 0.0

        # Maximum Drawdown
        peak = initial_capital
        max_dd = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd = dd
        max_dd_pct = round(max_dd * 100, 2)

        # Approximate annualized Sharpe ratio (daily step assumption)
        returns = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1]
            if prev > 0:
                returns.append((equity_curve[i] - prev) / prev)
        if len(returns) > 1:
            avg_ret = sum(returns) / len(returns)
            variance = sum((r - avg_ret) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = math.sqrt(variance) if variance > 0 else 1e-6
            sharpe = round((avg_ret / std_dev) * math.sqrt(365), 2)
        else:
            sharpe = 0.0

        summary = BacktestSummary(
            strategy_name="CRO_Support_Bounce_0.05719",
            symbol="CRO/USD",
            initial_capital_usd=initial_capital,
            final_capital_usd=round(final_capital, 2),
            total_return_pct=total_return_pct,
            total_trades=len(trades),
            winning_trades=winning_trades,
            win_rate_pct=win_rate,
            max_drawdown_pct=max_dd_pct,
            sharpe_ratio=sharpe,
            support_level_tested=support_level,
        )

        self._record_run(summary)
        return summary

    def _record_run(self, summary: BacktestSummary) -> None:
        run_id = f"run_{int(time.time())}_{summary.strategy_name}"
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO backtest_runs (
                        run_id, strategy_name, symbol, initial_capital_usd,
                        final_capital_usd, total_return_pct, total_trades,
                        win_rate_pct, max_drawdown_pct, sharpe_ratio,
                        support_level_tested, created_at, execution_mode
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        summary.strategy_name,
                        summary.symbol,
                        summary.initial_capital_usd,
                        summary.final_capital_usd,
                        summary.total_return_pct,
                        summary.total_trades,
                        summary.win_rate_pct,
                        summary.max_drawdown_pct,
                        summary.sharpe_ratio,
                        summary.support_level_tested,
                        time.time(),
                        summary.execution_mode,
                    ),
                )
        finally:
            conn.close()
