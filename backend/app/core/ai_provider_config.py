"""
NVIDIA NIM connection + per-service model selection.

All 7 AI services route through a single NVIDIA NIM endpoint (one OpenAI-compatible
API, one API key) — NIM hosts the third-party models (GLM, DeepSeek, MiniMax, Kimi,
Nemotron) behind a unified catalog, each addressed by its own model slug.

Model slugs below are confirmed exact for nemotron, deepseek, and both minimax
entries (from real NIM code samples). GLM and Kimi slugs are best-guess
(zai-org/ and moonshotai/ are NIM's standard org prefixes for those labs) —
override the matching *_MODEL env var if the catalog uses a different exact
slug (check https://build.nvidia.com for the model's own code sample).

Every value here is overridable via env vars (CLAUDE.md rule: no hardcoded
thresholds) — no code change needed to fix a wrong default.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProviderConnection:
    name: str
    base_url: str
    api_key_env: str


NIM = ProviderConnection(
    name="nvidia-nim",
    base_url=os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    api_key_env="NVIDIA_API_KEY",
)


@dataclass(frozen=True)
class ServiceModelConfig:
    connection: ProviderConnection
    model: str
    temperature: float = 1.0
    top_p: float = 0.95
    # Model-specific chat-template kwargs (e.g. thinking/reasoning toggles) —
    # passed through as OpenAI SDK's `extra_body`. Shape differs per model
    # family, so it's opaque here — see each ServiceModelConfig below.
    extra_body: Optional[dict] = None


# Nemotron: rationale is "fast, credit-efficient" (see the model table) — keep
# thinking off by default so Market Analyst stays fast on every call.
MARKET_ANALYST = ServiceModelConfig(
    NIM,
    model=os.getenv("MARKET_ANALYST_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)

STRATEGY_SELECTOR = ServiceModelConfig(NIM, model=os.getenv("STRATEGY_SELECTOR_MODEL", "zai-org/glm-5.1"))

# DeepSeek: rationale is "highest reasoning quality for money-critical
# decisions" — this is the one service where thinking should stay ON.
TRADE_VALIDATOR = ServiceModelConfig(
    NIM,
    model=os.getenv("TRADE_VALIDATOR_MODEL", "deepseek-ai/deepseek-v4-pro"),
    extra_body={"chat_template_kwargs": {"thinking": True}},
)

RISK_MANAGER = ServiceModelConfig(NIM, model=os.getenv("RISK_MANAGER_MODEL", "zai-org/glm-5.1"))
SENTIMENT_ANALYZER = ServiceModelConfig(NIM, model=os.getenv("SENTIMENT_ANALYZER_MODEL", "minimaxai/minimax-m3"))
CHAT_ASSISTANT = ServiceModelConfig(NIM, model=os.getenv("CHAT_ASSISTANT_MODEL", "moonshotai/kimi-k2.5"))
BACKTEST_EXPLAINER = ServiceModelConfig(NIM, model=os.getenv("BACKTEST_EXPLAINER_MODEL", "minimaxai/minimax-m2.7"))

# Pattern Explainer is called once per DETECTED PATTERN — potentially many
# times per scan, since explanations are auto-generated for every pattern
# found rather than on-demand. Same "fast, credit-efficient" rationale as
# Market Analyst, thinking off.
PATTERN_EXPLAINER = ServiceModelConfig(
    NIM,
    model=os.getenv("PATTERN_EXPLAINER_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)

# Analysis Explainer is on-demand only (one call per user click, synthesizing
# confluence across whichever tools are enabled at once) — unlike Pattern
# Explainer this isn't called automatically per result, so call volume is low.
ANALYSIS_EXPLAINER = ServiceModelConfig(
    NIM,
    model=os.getenv("ANALYSIS_EXPLAINER_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
