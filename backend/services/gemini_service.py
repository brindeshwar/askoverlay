import logging
from google import genai

log = logging.getLogger("askoverlay.gemini")

SYSTEM_INSTRUCTION = "You are a helpful assistant. Respond in plain text only. Do not use markdown, asterisks, bullet symbols, or special formatting."

async def stream_gemini_response(api_key: str, model: str, message: str, previous_interaction_id: str | None = None):
    client = genai.Client(api_key=api_key)
    new_interaction_id = None
    event_count = 0

    kwargs = {
        "model": model,
        "input": message,
        "system_instruction": SYSTEM_INSTRUCTION,
        "stream": True,
    }
    if previous_interaction_id:
        kwargs["previous_interaction_id"] = previous_interaction_id

    log.info(f"Calling Gemini: model={model}, has_previous_id={bool(previous_interaction_id)}")

    try:
        stream = await client.aio.interactions.create(**kwargs)
        async for event in stream:
            event_count += 1
            log.info(f"Event #{event_count}: type={event.event_type}")
            if event.event_type == "step.delta" and event.delta.type == "text":
                yield f"data: {event.delta.text}\n\n"
            elif event.event_type == "interaction.completed":
                new_interaction_id = event.interaction.id
                log.info(f"Completed: id={new_interaction_id}, usage={event.interaction.usage}")
            elif event.event_type == "error":
                log.error(f"Gemini stream error event: {event.error.message} (code={event.error.code})")
                yield f"data: [ERROR: {event.error.message}]\n\n"
        log.info(f"Stream ended. Total events: {event_count}")
    except Exception as e:
        log.error(f"Exception during stream: {e}", exc_info=True)
        yield f"data: [ERROR: {str(e)}]\n\n"
    finally:
        if new_interaction_id:
            yield f"data: [INTERACTION_ID:{new_interaction_id}]\n\n"
        yield "data: [DONE]\n\n"