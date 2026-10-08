import asyncio

import pytest
from langchain_core.exceptions import (
    ModelAPIError,
    ModelInvalidRequestError,
    ModelRateLimitError,
)
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage

from agent.graph import SYSTEM_PROMPT, build_graph, to_messages, visible_text
from tests.fakes import ScriptedChat


def run(graph, text="hello"):
    """Run the graph and return (streamed visible text, nodes that produced tokens)."""

    async def go():
        out, nodes = "", []
        async for chunk, meta in graph.astream(
            {"messages": to_messages([], text), "failed_over": False}, stream_mode="messages"
        ):
            out += visible_text(chunk)
            if meta["langgraph_node"] not in nodes:
                nodes.append(meta["langgraph_node"])
        return out, nodes

    return asyncio.run(go())


def test_primary_answers_and_fallback_is_untouched():
    primary, fallback = ScriptedChat(model="p", script=["Hel", "lo"]), ScriptedChat(model="f", script=["unused"])
    out, nodes = run(build_graph(primary, fallback))
    assert out == "Hello"
    assert nodes == ["primary"]
    assert (primary.calls, fallback.calls) == (1, 0)


def test_transient_failure_before_any_text_fails_over():
    primary = ScriptedChat(model="p", script=[ModelRateLimitError("429")])
    fallback = ScriptedChat(model="f", script=["from ", "fallback"])
    out, nodes = run(build_graph(primary, fallback))
    assert out == "from fallback"
    assert nodes == ["fallback"]
    assert (primary.calls, fallback.calls) == (1, 1)


def test_server_error_before_any_text_fails_over():
    out, _ = run(build_graph(ScriptedChat(script=[ModelAPIError("500")]), ScriptedChat(script=["ok"])))
    assert out == "ok"


def test_failure_after_text_was_shown_does_not_fail_over():
    """A second model would restart the answer and the user would read it twice."""
    primary = ScriptedChat(model="p", script=["partial ", ModelAPIError("died mid-answer")])
    fallback = ScriptedChat(model="f", script=["restart"])
    with pytest.raises(ModelAPIError):
        run(build_graph(primary, fallback))
    assert fallback.calls == 0


def test_reasoning_only_output_does_not_count_as_shown():
    primary = ScriptedChat(script=[{"type": "thinking", "thinking": "hmm"}, ModelRateLimitError("429")])
    out, nodes = run(build_graph(primary, ScriptedChat(script=["answer"])))
    assert out == "answer" and nodes[-1] == "fallback"


@pytest.mark.parametrize("error", [ModelInvalidRequestError("API key not valid")])
def test_non_transient_errors_do_not_fail_over(error):
    """A bad key or request would fail identically on the fallback, so don't pay for a second call."""
    fallback = ScriptedChat(script=["unused"])
    with pytest.raises(type(error)):
        run(build_graph(ScriptedChat(script=[error]), fallback))
    assert fallback.calls == 0


def test_both_models_failing_raises_the_fallbacks_error():
    graph = build_graph(ScriptedChat(script=[ModelRateLimitError("p")]), ScriptedChat(script=[ModelAPIError("f")]))
    with pytest.raises(ModelAPIError):
        run(graph)


def test_without_a_fallback_transient_errors_propagate():
    with pytest.raises(ModelRateLimitError):
        run(build_graph(ScriptedChat(script=[ModelRateLimitError("429")]), fallback=None))


def test_to_messages_orders_system_history_then_new_message():
    msgs = to_messages([("user", "hi"), ("assistant", "hello")], "next")
    assert [type(m) for m in msgs] == [SystemMessage, HumanMessage, AIMessage, HumanMessage]
    assert msgs[0].content == SYSTEM_PROMPT
    assert msgs[-1].content == "next"


def test_visible_text_ignores_reasoning_blocks_and_non_chunks():
    chunk = AIMessageChunk(content=[{"type": "thinking", "thinking": "secret"}, {"type": "text", "text": "shown"}])
    assert visible_text(chunk) == "shown"
    assert visible_text(AIMessage("full message, not a chunk")) == ""
    assert visible_text(AIMessageChunk(content="plain")) == "plain"
