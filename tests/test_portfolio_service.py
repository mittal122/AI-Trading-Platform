from backend.app.schemas.execution import OrderSide

from backend.app.services.execution.execution_factory import (
    ExecutionFactory,
)

from backend.app.services.portfolio.portfolio_factory import (
    PortfolioFactory,
)


portfolio = PortfolioFactory.get_engine()

execution = ExecutionFactory.get_engine()


buy = execution.execute(
    side=OrderSide.BUY,
    price=60000,
    quantity=0.1,
)

portfolio.buy(buy)

portfolio.update_market_price(
    61000,
)

print("After BUY")
print(portfolio.get_state().model_dump())


sell = execution.execute(
    side=OrderSide.SELL,
    price=61000,
    quantity=0.1,
)

portfolio.sell(sell)

print()

print("After SELL")
print(portfolio.get_state().model_dump())