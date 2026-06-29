import os
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

    def __init__(self):
        self.predictor = None
        self.loaded = False

    def load(self):

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
            model,
            tokenizer,
            device=device,
            max_context=512,
        )

        self.loaded = True

        print(f"Kronos loaded on {device}")