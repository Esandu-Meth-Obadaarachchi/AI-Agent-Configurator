"""Chat model factory. Every model call in the app goes through get_chat_model().

Claude notes, current as of October 2026:
- Claude Opus 5.5, Sonnet 5.5 and Fable reject sampling settings (temperature,
  top_p, top_k). Temperature is only sent to models that accept it.
- Depth of reasoning is controlled with `effort` (low, medium, high, xhigh, max).
- Forced tool use is rejected on the newest models, so structured decisions use
  native structured outputs (method="json_schema"), never a forced tool call.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from app.config import get_settings

_NO_SAMPLING = ("claude-opus-5", "claude-sonnet-5", "claude-fable-5", "claude-mythos", "claude-opus-4-7", "claude-opus-4-8")
_NO_EFFORT = ("claude-haiku", "claude-3")
_REFUSAL_FALLBACK = ("claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1")


def get_chat_model(
    model: str | None = None,
    *,
    temperature: float | None = None,
    effort: str | None = None,
    purpose: str = "chat",
) -> BaseChatModel:
    """Return a chat model. `purpose` only labels demo-mode replies."""
    settings = get_settings()
    name = model or settings.llm_model
    if settings.llm_provider == "fake":
        from app.demo import DemoChatModel

        return DemoChatModel(purpose=purpose)
    if name.startswith("claude-"):
        return _anthropic(name, temperature, effort)
    return _openai(name, temperature)


def structured(llm: BaseChatModel, schema: type) -> Runnable[Any, Any]:
    """A model that answers with an instance of `schema`, using native structured output.

    Tagged "nostream" so routing decisions don't stream into the chat as text.
    """
    return llm.with_structured_output(schema, method="json_schema").with_config(tags=["nostream"])


def _anthropic(name: str, temperature: float | None, effort: str | None) -> BaseChatModel:
    from langchain_anthropic import ChatAnthropic

    settings = get_settings()
    kwargs: dict[str, Any] = {"model": name, "max_tokens": settings.llm_max_tokens}
    if settings.anthropic_api_key:
        kwargs["api_key"] = settings.anthropic_api_key
    if not name.startswith(_NO_SAMPLING):
        kwargs["temperature"] = temperature if temperature is not None else settings.llm_temperature
    chosen_effort = effort or settings.llm_effort
    if chosen_effort and not name.startswith(_NO_EFFORT):
        kwargs["reasoning_effort"] = chosen_effort
    if settings.anthropic_refusal_fallback == "default" and name.startswith(_REFUSAL_FALLBACK):
        # If a safety classifier declines, the API retries on a fallback model in the same call.
        kwargs["betas"] = ["server-side-fallback-2026-07-01"]
        kwargs["model_kwargs"] = {"fallbacks": "default"}
    return ChatAnthropic(**kwargs)


def _openai(name: str, temperature: float | None) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    kwargs: dict[str, Any] = {"model": name, "max_tokens": settings.llm_max_tokens}
    if settings.openai_api_key:
        kwargs["api_key"] = settings.openai_api_key
    if temperature is not None or not name.startswith(("gpt-5", "o")):
        kwargs["temperature"] = temperature if temperature is not None else settings.llm_temperature
    return ChatOpenAI(**kwargs)
