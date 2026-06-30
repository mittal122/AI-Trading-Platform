from backend.app.services.position.position_factory import (
    PositionFactory,
)

engine = PositionFactory.get_engine()

result = engine.calculate(
    account_equity=10000,
    entry=60000,
    stop_loss=59500,
    risk_percent=1,
)

print(result.model_dump())