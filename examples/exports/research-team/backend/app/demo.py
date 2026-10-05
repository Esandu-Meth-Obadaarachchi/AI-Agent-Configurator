"""Offline demo model (LLM_PROVIDER=fake).

Lets you click through the whole app and run the test suite with no API key and no
cost. It never calls tools and answers every structured decision with the schema's
`demo()` value, which follows the happy path.
"""

from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda

from app.messages import text_of


class DemoChatModel(BaseChatModel):
    purpose: str = "chat"

    @property
    def _llm_type(self) -> str:
        return "demo"

    def _reply(self, messages: Sequence[BaseMessage]) -> str:
        last = next((m for m in reversed(messages) if m.type == "human"), None)
        said = " ".join(text_of(last).split())[:160] if last else ""
        return (
            f"**{self.purpose}** (demo mode): I received \"{said}\". "
            "Set LLM_PROVIDER and your API key in .env to get real answers."
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self._reply(messages)))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        words = self._reply(messages).split(" ")
        for i, word in enumerate(words):
            token = word if i == 0 else " " + word
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))
            if run_manager:
                run_manager.on_llm_new_token(token, chunk=chunk)
            time.sleep(0.01)
            yield chunk

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable[Any, Any]:  # type: ignore[override]
        return self

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Runnable[Any, Any]:  # type: ignore[override]
        def answer(_: Any) -> Any:
            return schema.demo() if hasattr(schema, "demo") else schema()

        return RunnableLambda(answer)
