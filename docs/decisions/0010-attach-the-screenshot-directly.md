# ADR-0010: Attach the screenshot directly when the user turns screen reading on

- Status: Accepted
- Date: 2026-10-16
- Related: Supersedes **Decision 2 ("Middle" capture strategy)** of [ADR-0003](0003-screen-context-via-vision-not-ocr.md). Its
  Decision 1 (vision, not OCR) and its privacy rule (never stored or logged) stay in force.

## Context

ADR-0003 designed the screen-reading feature so that the client captures a screenshot on every send, the backend declares a
`read_screen` tool, and the model decides whether to call it. The feature was never built. Building it now showed two costs of
that design:

- A tool call is **two model calls** (ask, tool result, answer). Answers already take 2 to 17 seconds on the free tier, so the
  tool loop roughly doubles the wait for every screen question.
- It needs a tool loop in the LangGraph agent and a failover story across two calls, which is the most complex part of the
  feature for the least benefit. The screenshot is uploaded on every send either way, so the privacy exposure of the tool
  design is no smaller.

## Options considered

1. **Keep ADR-0003's tool design.** Faithful to the old plan; the model skips the image for non-screen questions.
2. **Attach the screenshot to the message directly while the user has "Look at my screen" on** (this ADR). One model call, a much
   simpler agent. The cost is image tokens on every message while the switch is on.

## Decision

Option 2. The client has a "Look at my screen" switch, **off by default and remembered between runs**. While it is on, each send
captures one screenshot of the screen that holds the chat window (with the chat window itself excluded from the capture),
downsizes it, and sends it with that message only. The backend attaches it to the user's message as an image. The screenshot
is **not** part of the saved conversation history; a follow-up question captures a fresh one. Demo requests with a screenshot
count as one request like any other.

## Consequences

- Faster and simpler, but every message sent with the switch on spends image tokens. The user controls the switch; the demo
  daily caps still bound total spend, and the heavier requests use the shared budget faster (noted in the README).
- Privacy: the screenshot goes to Google's model. It is never stored or logged by the backend (a log filter redacts embedded
  images as a second line of defence). Whether Google may use free-tier prompts to improve its products is still unverified
  (see STATUS); the client shows a one-time notice the first time the switch is turned on.
- If a future feature needs the model to *choose* whether to look (for example with several tools), this decision can be
  revisited with a new ADR.

## How we will know it was right

A real run in which a model reads a known error code from a captured screenshot, tests with fake models for every piece, and
no screenshot data in any log.
