from typing import Optional

from pydantic import BaseModel, Field


class SaveBinanceKeysRequest(BaseModel):
    api_key: str = Field(min_length=10, max_length=200)
    api_secret: str = Field(min_length=10, max_length=200)


class BinanceKeyStatus(BaseModel):
    configured: bool
    key_preview: Optional[str] = None
