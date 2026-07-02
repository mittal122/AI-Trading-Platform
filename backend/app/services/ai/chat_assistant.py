from backend.app.core.ai_provider_config import CHAT_ASSISTANT
from backend.app.schemas.ai import ChatRequest, ChatResponse
from backend.app.services.ai.llm_client import MultiProviderAIService

_SYSTEM = """You are an AI assistant for a professional algorithmic trading platform.
You help traders understand market signals, portfolio performance, risk management, and trading strategies.
Be concise, precise, and data-driven. Focus on actionable insights.
Do not give financial advice — explain what the data shows and how the system works."""


class ChatAssistant(MultiProviderAIService):

    def __init__(self) -> None:
        super().__init__(CHAT_ASSISTANT)

    def chat(self, req: ChatRequest) -> ChatResponse:
        messages = [
            {"role": m.role, "content": m.content} for m in req.history
        ]
        messages.append({"role": "user", "content": req.message})

        reply = self._chat(_SYSTEM, messages, max_tokens=2048)
        return ChatResponse(reply=reply)
