from dotenv import load_dotenv
import os

load_dotenv()

class Settings:

    KRONOS_PATH = os.getenv("KRONOS_PATH")

    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL")

    DEFAULT_TOKENIZER = os.getenv("DEFAULT_TOKENIZER")

    DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL")

    DEFAULT_INTERVAL = os.getenv("DEFAULT_INTERVAL")

    DEFAULT_LOOKBACK = int(os.getenv("DEFAULT_LOOKBACK"))

    DEFAULT_PRED_LEN = int(os.getenv("DEFAULT_PRED_LEN"))


settings = Settings()