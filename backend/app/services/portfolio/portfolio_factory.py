from backend.app.services.portfolio.simple_portfolio import (
    SimplePortfolio,
)


class PortfolioFactory:

    @staticmethod
    def get_engine(
        name: str = "simple",
    ):

        engines = {
            "simple": SimplePortfolio,
        }

        name = name.lower()

        if name not in engines:

            raise ValueError(
                f"Unknown portfolio engine: {name}"
            )

        return engines[name]()