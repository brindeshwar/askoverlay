"""The chat agent as a LangGraph graph.

    START -> primary --(answered)--------------------------> END
                 \\--(transient failure, nothing shown yet)--> fallback -> END

The server is stateless: the client sends the conversation so far with every request, so the graph is
compiled without a checkpointer and holds nothing between requests.
"""
import logging
from typing import Protocol

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from agent.errors import is_transient

log = logging.getLogger("askoverlay.agent")

SYSTEM_PROMPT = (
    "You are a helpful assistant. Use markdown formatting naturally where it helps clarity "
    "(headers, bold, bullet points, code blocks)."
)


class AgentState(MessagesState):
    failed_over: bool


class StreamingChatModel(Protocol):
    """What the graph needs from a model (satisfied by LangChain chat models and by test fakes)."""

    model: str

    def astream(self, messages: list[BaseMessage]): ...


def visible_text(chunk: object) -> str:
    """The user-visible text of a streamed chunk (ignores reasoning blocks and non-chunks)."""
    if not isinstance(chunk, AIMessageChunk):
        return ""
    content = chunk.content
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )


def to_messages(history: list[tuple[str, str]], message: str) -> list[BaseMessage]:
    """System prompt + the client-supplied history (role, text) + the new user message."""
    messages: list[BaseMessage] = [SystemMessage(SYSTEM_PROMPT)]
    for role, content in history:
        messages.append(HumanMessage(content) if role == "user" else AIMessage(content))
    messages.append(HumanMessage(message))
    return messages


def build_graph(primary: StreamingChatModel, fallback: StreamingChatModel | None = None):
    """Compile the graph around already-built models.

    Models are captured in closures rather than passed through graph config on purpose: they hold
    the caller's API key, and config values can end up in tracing metadata.
    """

    async def answer(model: StreamingChatModel, state: AgentState, can_fail_over: bool) -> dict:
        shown_to_user = False
        final: AIMessageChunk | None = None
        try:
            async for chunk in model.astream(state["messages"]):
                if visible_text(chunk):
                    shown_to_user = True
                final = chunk if final is None else final + chunk
        except Exception as exc:
            # Fail over only if the user has seen nothing yet; after that a second model would
            # start the answer over and the user would read a duplicated, garbled reply.
            if can_fail_over and not shown_to_user and is_transient(exc):
                log.warning(f"{model.model} failed before answering ({type(exc).__name__}); trying the fallback model")
                return {"failed_over": True}
            raise
        return {"messages": [final if final is not None else AIMessage("")], "failed_over": False}

    async def primary_node(state: AgentState) -> dict:
        return await answer(primary, state, can_fail_over=fallback is not None)

    async def fallback_node(state: AgentState) -> dict:
        assert fallback is not None
        return await answer(fallback, state, can_fail_over=False)

    def after_primary(state: AgentState) -> str:
        return "fallback" if state.get("failed_over") else END

    graph = StateGraph(AgentState)
    graph.add_node("primary", primary_node)
    graph.add_edge(START, "primary")
    if fallback is not None:
        graph.add_node("fallback", fallback_node)
        graph.add_conditional_edges("primary", after_primary, ["fallback", END])
        graph.add_edge("fallback", END)
    else:
        graph.add_edge("primary", END)
    return graph.compile()
