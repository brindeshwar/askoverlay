# ADR-0003: Screen context via vision, not OCR; "Middle" capture strategy

- Status: Accepted
- Date: 2026-10-09
- Status detail: Accepted - open question resolved

- Vision, not OCR: UI screenshots (small antialiased fonts, text in controls, layout that carries
  meaning) defeat traditional OCR, and the task is screen understanding, not transcription.
- "Middle" strategy: the client captures one screenshot per send and attaches it; the backend declares a
  `read_screen` tool and the model decides whether to use it. If the model does not call the tool, the
  screenshot is discarded and non-screen questions cost nothing extra.
- Privacy: screenshot captured, sent, discarded if unused, never stored or logged. (See the free-tier
  caveat in ADR-0007.)

**Open question, now resolved.** Can the cheap model read UI screenshots, and can an image be returned
as a tool result? Live spike on 2026-10-09 (synthetic error-dialog screenshot, via LangChain
`ChatGoogleGenerativeAI`): `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite` both read the error code
correctly from an image in a user message, and both answered correctly when the image was returned
*inside* a `ToolMessage`. `gemini-2.5-flash-lite` was not tested (Google now restricts 2.5 models to
existing users). Known limitation: combining Google's built-in tools (e.g. search) with custom
functions is not supported on the newest models through the Interactions API.
