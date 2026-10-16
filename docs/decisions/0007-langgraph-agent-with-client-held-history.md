# ADR-0007: LangGraph for the agent; the client holds conversation history

- Status: Accepted
- Date: 2026-10-09
- Status detail: Accepted and implemented (default models chosen by the owner)

**Context.** The owner wants LangChain/LangGraph. ADR-0001's server-side memory conflicts with removing
accounts and with privacy (chats stored outside our control), so history moves to the client: each
request carries the prior turns and the server is stateless.

**What the framework earns, honestly.** With history on the client there is no checkpointer, so the
persistence argument for LangGraph disappears. What remains: a graph with explicit nodes and a
conditional edge (`agent` -> `screen` tool node -> `agent`), a standard message/tool-call abstraction
across providers, and token streaming (`stream_mode="messages"`). With a single tool this is a small
graph; the stronger story arrives with a second tool (V1.2). If that is never built, a plain tool loop
would be equally correct and simpler. This is a deliberate trade, recorded so it is defensible.

**Spike results (2026-10-09, live, `langchain-google-genai` 4.4.0, `langgraph` 1.2.14, synthetic
screenshot).** Checks: plain invoke, token streaming, vision in a user message, tool call requested for a
screen question, no tool call for a non-screen question, image inside a ToolMessage, image in a following
user message (fallback), full LangGraph run with a streamed answer, and a stateless run with
client-supplied history.

Follow-up benchmark, same day: 12 interleaved rounds (so a slow period hits every model equally), two
workloads per model - a short text prompt and the product-critical "read the error code from this
screenshot" prompt - on the free-tier backend key. Times are seconds to first streamed token.

| Model | Text median / p90 | Vision median / p90 | Failures (of 24) | Vision accuracy |
|---|---|---|---|---|
| `gemini-3.1-flash-lite` | 1.5 / 8.6 | 1.7 / 3.9 | 0 | 12/12 |
| `gemini-3.5-flash-lite` | 7.1 / 10.9 | 8.4 / 16.3 | 0 | 12/12 |
| `gemini-3.5-flash` | 3.3 / 10.1 | 2.3 / 3.4 | 5 (HTTP 429) | 9/9 |
| `gemini-3.8-flash` | 20.5 / 65.9 | 4.4 / 6.0 | 13 (HTTP 429) | 5/5 |

Reading it: both lite models were 100% accurate and reliable on this key, but `3.5-flash-lite` was about
4-5x slower to first token than `3.1-flash-lite` (the earlier Interactions API timings of 11 s and 47 s
fit this pattern, so LangChain is not the cause, and `thinking_level` made no difference). The two
larger models are fast when they answer but hit free-tier quota limits, so they are unusable for a
backend-funded demo. Caveats: n = 12 per cell, one day, one free-tier key; latency on a free tier can
shift with load, and this run consumed part of that day's quota for the larger models.

**Recommendation.** Default to `gemini-3.1-flash-lite` for interactive use (the model is a config value,
`GEMINI_MODEL`, so this is a one-line change); keep `gemini-3.5-flash-lite` as an option. Re-measure on a
paid key before promising anything about production latency.

**Known risks.** `langchain-google-genai` pulls a much newer `google-genai` (2.29) than the backend pins
(2.10); the migration replaces the direct SDK dependency. Earlier reports of Gemini 3 thought-signature
errors on tool calls did not reproduce here, but the area is fast-moving: pin versions.

**Privacy caveat to verify.** Gemini API free-tier content may be used by Google to improve its
products; if so, screenshots sent through the free demo key contradict "never stored". Check the current
terms before making that claim, or send screenshots only on BYOK / a paid key.

**Correction (same day, later).** A second, unrelated test (the pointing eval, 16 calls per model) showed the
reverse ordering: `3.5-flash-lite` median 1.9 s, `3.1-flash-lite` median 13.4 s. Free-tier latency is
dominated by API load and varies hour to hour, so the "3.1 is several times faster" finding above should be
read as "latency on this key is unpredictable", not as a property of either model. This is the argument for
the fallback arrangement, and against tuning the primary/fallback order on small samples. Re-measure on a
paid key, with timing spread over several days, before drawing any conclusion about speed.

**Decision (owner).** Primary `gemini-3.5-flash-lite`, fallback `gemini-3.1-flash-lite`, both configurable
(`GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`). The benchmark above recommended the reverse order for speed;
the owner kept 3.5 as primary, and the fallback also covers its slow tail only on failures (rate limit,
5xx, timeout), not on slowness alone. Revisit with a latency-triggered fallback or a swap if first-token
times hurt in practice.

**Implemented.**
- `agent/graph.py`: `primary -> (answered | transient failure and nothing shown yet -> fallback)`. Failover
  happens only if the user has seen no text; a failure after text was shown surfaces in-band, because a
  second model would restart the answer and the user would read it twice. Reasoning-only output does not
  count as shown.
- `agent/errors.py`: failures classified with LangChain's provider-neutral exception types. Bad key or
  request means no fallback (it would fail identically). Library retries are off for the primary and one
  for the fallback, because the library's backoff waits tens of seconds on a 429.
- `services/chat_service.py`: runs the graph until the first visible text before returning, so up-front
  failures become real HTTP statuses. Errors after streaming starts use a raw `[ERROR: ...]` frame that
  cannot be confused with JSON-quoted model text.
- Models are built per request in closures, not graph config, since config can reach tracing metadata and
  the models hold the caller's API key.
- Verified live: streaming, memory carried by the client, invalid key -> 400, and 5/5 real failovers
  when the primary was genuinely rate-limited.

**Next.** `read_screen` tool node (V1.1); the screenshot must be removed from the history returned to
the client.
