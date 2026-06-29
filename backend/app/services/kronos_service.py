import sys
import pandas as pd
import torch

from backend.app.core.config import settings

# Add Kronos repository to Python path
if settings.KRONOS_PATH not in sys.path:
    sys.path.insert(0, settings.KRONOS_PATH)

from model import (
    Kronos,
    KronosTokenizer,
    KronosPredictor,
)


class KronosService:
    """
    Singleton service responsible for interacting with the Kronos AI model.
    """

    def __init__(self):
        self.predictor = None
        self.loaded = False

    def load(self):
        """
        Load the Kronos model only once.
        """

        if self.loaded:
            return

        print("Loading Kronos Model...")

        tokenizer = KronosTokenizer.from_pretrained(
            settings.DEFAULT_TOKENIZER
        )

        model = Kronos.from_pretrained(
            settings.DEFAULT_MODEL
        )

        device = "cuda" if torch.cuda.is_available() else "cpu"

        self.predictor = KronosPredictor(
            model=model,
            tokenizer=tokenizer,
            device=device,
            max_context=512,
        )

        self.loaded = True

        print(f"Kronos loaded on {device}")

    def is_loaded(self) -> bool:
        """
        Returns True if the model is already loaded.
        """
        return self.loaded

    def predict(
        self,
        df: pd.DataFrame,
        pred_len: int,
    ) -> pd.DataFrame:
        """
        Generate future OHLCV predictions.
        """

        if not self.loaded:
            raise RuntimeError(
                "Kronos model is not loaded."
            )

        x_timestamp = pd.Series(df["timestamps"])

        y_timestamp = self._create_future_timestamps(
            timestamps=x_timestamp,
            pred_len=pred_len,
        )

        prediction = self.predictor.predict(
            df=df[
                [
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "amount",
                ]
            ],
            x_timestamp=x_timestamp,
            y_timestamp=y_timestamp,
            pred_len=pred_len,
        )

        return prediction

    def _create_future_timestamps(
        self,
        timestamps: pd.Series,
        pred_len: int,
    ) -> pd.Series:
        """
        Generate future timestamps based on
        the interval of the historical data.
        """

        timestamps = pd.Series(
            pd.to_datetime(timestamps)
        )

        interval = (
            timestamps.iloc[-1]
            - timestamps.iloc[-2]
        )

        future = pd.date_range(
            start=timestamps.iloc[-1] + interval,
            periods=pred_len,
            freq=interval,
        )

        return pd.Series(future)