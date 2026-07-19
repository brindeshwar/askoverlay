from google import genai

SYSTEM_INSTRUCTION = "You are a helpful assistant. Respond in plain text only. Do not use markdown, asterisks, bullet symbols, or special formatting."

async def stream_gemini_response(api_key: str, model: str, message: str, previous_interaction_id: str | None = None):
    client = genai.Client(api_key=api_key)
    new_interaction_id = None

    kwargs = {
        "model": model,
        "input": message,
        "system_instruction": SYSTEM_INSTRUCTION,
        "stream": True,
    }
    if previous_interaction_id:
        kwargs["previous_interaction_id"] = previous_interaction_id

    try:
        stream = await client.aio.interactions.create(**kwargs)
        async for event in stream:
            if event.event_type == "step.delta" and event.delta.type == "text":
                yield f"data: {event.delta.text}\n\n"
            elif event.event_type == "interaction.completed":
                new_interaction_id = event.interaction.id
    except Exception as e:
        yield f"data: [ERROR: {str(e)}]\n\n"
    finally:
        if new_interaction_id:
            yield f"data: [INTERACTION_ID:{new_interaction_id}]\n\n"
        yield "data: [DONE]\n\n"