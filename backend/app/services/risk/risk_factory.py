from backend.app.services.risk.atr_risk import (
    ATRRisk,
)


class RiskFactory:

    @staticmethod
    def get_engine(
        name: str = "atr",
    ):

        engines = {
            "atr": ATRRisk,
        }

        name = name.lower()

        if name not in engines:
            raise ValueError(
                f"Unknown risk engine: {name}"
            )

        return engines[name]()