from backend.app.schemas.execution import OrderSide

from backend.app.services.execution.execution_factory import (
    ExecutionFactory,
)

engine = ExecutionFactory.get_engine()

print("BUY")
print(
    engine.execute(
        side=OrderSide.BUY,
        price=60000,
        quantity=0.25,
    ).model_dump()
)

print()

print("SELL")
print(
    engine.execute(
        side=OrderSide.SELL,
        price=60000,
        quantity=0.25,
    ).model_dump()
)