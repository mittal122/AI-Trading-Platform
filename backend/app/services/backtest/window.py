import pandas as pd


class WindowGenerator:

    @staticmethod
    def generate(
        market: pd.DataFrame,
        minimum_history: int = 200,
    ):

        for i in range(
            minimum_history,
            len(market),
        ):

            yield market.iloc[: i + 1]