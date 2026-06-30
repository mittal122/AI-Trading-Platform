from backend.app.services.backtest.simple_backtest import (
    SimpleBacktest,
)


class BacktestFactory:

    @staticmethod
    def get_engine(
        name: str = "simple",
    ):

        engines = {
            "simple": SimpleBacktest,
        }

        name = name.lower()

        if name not in engines:

            raise ValueError(
                f"Unknown backtest engine: {name}"
            )

        return engines[name]()