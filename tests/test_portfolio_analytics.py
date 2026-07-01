from backend.app.services.backtest.backtest_factory import BacktestFactory
from backend.app.services.portfolio.analytics import PortfolioAnalytics

engine = BacktestFactory.get_engine()
result = engine.run(strategy="rsi", symbol="BTCUSDT", interval="5m", limit=300)

analytics = PortfolioAnalytics()
report = analytics.compute(
    trades=result.trades,
    equity_curve=result.equity_curve,
    initial_balance=result.initial_balance,
)

print("\n========== PORTFOLIO ANALYTICS ==========\n")
print(f"Initial Balance  : ${report.initial_balance:,.2f}")
print(f"Ending Balance   : ${report.ending_balance:,.2f}")
print(f"Total Return     : {report.total_return:.4f}%")
print(f"Total Trades     : {report.total_trades}")
print()
print(f"Win Rate         : {report.win_rate:.2f}%  ({report.winning_trades}W / {report.losing_trades}L)")
print(f"Avg Win          : ${report.avg_win:.4f}")
print(f"Avg Loss         : ${report.avg_loss:.4f}")
print()
print(f"Profit Factor    : {report.profit_factor:.4f}")
print(f"Expectancy       : ${report.expectancy:.4f} per trade")
print()
print(f"Sharpe Ratio     : {report.sharpe_ratio:.4f}")
print(f"Sortino Ratio    : {report.sortino_ratio:.4f}")
print(f"Calmar Ratio     : {report.calmar_ratio:.4f}")
print()
print(f"Max Drawdown     : {report.max_drawdown:.4f}%")
