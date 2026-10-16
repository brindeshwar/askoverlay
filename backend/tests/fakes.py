"""A scripted chat model. It must be a real LangChain BaseChatModel (not a bare class with astream):
LangGraph's token streaming works through the callbacks a real chat model fires."""
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult


class ScriptedChat(BaseChatModel):
    """Plays back a script: strings are streamed as text tokens, exceptions are raised, dicts are
    emitted as raw content blocks (e.g. a reasoning block)."""

    model: str = "fake"
    script: list[Any] = []
    calls: int = 0
    seen: list[Any] = []  # the messages each call received
    closed: bool = False

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        text = "".join(item for item in self.script if isinstance(item, str))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(text))])

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls += 1
        self.seen.append(list(messages))
        for item in self.script:
            if isinstance(item, BaseException):
                raise item
            content = [item] if isinstance(item, dict) else item
            yield ChatGenerationChunk(message=AIMessageChunk(content=content))

    async def aclose(self) -> None:
        self.closed = True
