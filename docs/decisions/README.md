# Decision log (ADRs)

One file per architecturally significant decision. A decision is **never edited after it is accepted** except to
change its status or add a "Related" note: to change your mind, write a new ADR that supersedes the old one, so the
history of *why* stays intact. How and when to write one: see
[documentation-and-memory-policy](../06-process/documentation-and-memory-policy.md). Start from
[the template](../templates/adr-template.md).

Statuses: **Proposed** (under review), **Accepted**, **Superseded** (replaced, see the Related line),
**Rejected**, **Deprecated**.

| ADR | Decision | Status | Date |
|---|---|---|---|
| [ADR-0001](0001-single-llm-seam-via-gemini-interactions-api.md) | Single LLM seam via the Gemini Interactions API | Superseded | 2026-10-05 |
| [ADR-0002](0002-raw-function-calling-not-an-agent-framework.md) | Raw function calling, not an agent framework | Superseded | 2026-10-05 |
| [ADR-0003](0003-screen-context-via-vision-not-ocr.md) | Screen context via vision, not OCR; "Middle" capture strategy | Accepted | 2026-10-09 |
| [ADR-0004](0004-db-session-lifecycle-and-client-split.md) | DB session lifecycle via `get_db`; client UI/dialogs split | Accepted | 2026-10-05 |
| [ADR-0005](0005-byok-plus-lifetime-demo.md) | BYOK plus a lifetime demo; no accounts, no payments | Accepted | 2026-10-09 |
| [ADR-0006](0006-demo-abuse-model.md) | Demo abuse model - per-IP and global daily caps, atomic and all-or-nothing | Accepted | 2026-10-09 |
| [ADR-0007](0007-langgraph-agent-with-client-held-history.md) | LangGraph for the agent; the client holds conversation history | Accepted | 2026-10-09 |
| [ADR-0008](0008-product-direction-show-me-where.md) | Product direction "show me where" - GO by the pre-registered rule, with caveats | Accepted | 2026-10-12 |
| [ADR-0009](0009-pivot-to-an-ai-test-agent.md) | Make the product an AI test agent | Proposed | 2026-10-12 |
| [ADR-0010](0010-repository-as-the-projects-memory.md) | The repository is the project's memory | Proposed | 2026-10-12 |
| [ADR-0011](0011-verdict-is-computed-from-assertions.md) | The verdict is computed from recorded assertions, never from the model's opinion | Proposed | 2026-10-12 |
| [ADR-0012](0012-mcp-surface-as-plain-tools.md) | The MCP surface is plain tools; the experimental Tasks feature is optional | Proposed | 2026-10-12 |
| [ADR-0013](0013-local-first-core-with-optional-service-mode.md) | A local-first core, with a designed but unbuilt service mode | Proposed | 2026-10-12 |
