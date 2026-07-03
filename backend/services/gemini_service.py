from google import genai
from google.genai import types

SYSTEM_INSTRUCTION = "You are a helpful assistant. Respond in plain text only. Do not use markdown, asterisks, bullet symbols, or special formatting."

async def stream_gemini_response(api_key: str, model: str, message: str):
    client = genai.Client(api_key=api_key)
    try:
        async for chunk in await client.aio.models.generate_content_stream(
            model=model,
            contents=message,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
        ):
            if chunk.text:
                yield f"data: {chunk.text}\n\n"
    except Exception as e:
        yield f"data: [ERROR: {str(e)}]\n\n"
    finally:
        yield "data: [DONE]\n\n"