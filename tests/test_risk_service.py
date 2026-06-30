from backend.app.schemas.risk import Direction

from backend.app.services.risk.risk_factory import (
    RiskFactory,
)

engine = RiskFactory.get_engine()

print("LONG")
print(
    engine.calculate(
        direction=Direction.LONG,
        entry=60000,
        atr=250,
    ).model_dump()
)

print()

print("SHORT")
print(
    engine.calculate(
        direction=Direction.SHORT,
        entry=60000,
        atr=250,
    ).model_dump()
)

print()

print("FLAT")
print(
    engine.calculate(
        direction=Direction.FLAT,
        entry=60000,
        atr=250,
    ).model_dump()
)