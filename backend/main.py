from fastapi import FastAPI, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
from google.genai import types

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest, x_gemini_key: str = Header(...)):
    client = genai.Client(api_key=x_gemini_key)

    async def generate():
        try:
            async for chunk in await client.aio.models.generate_content_stream(
                model="gemini-3.5-flash",
                contents=request.message,
                config=types.GenerateContentConfig(
                    system_instruction="You are a helpful assistant. Respond in plain text only. Do not use markdown, asterisks, bullet symbols, or special formatting."
                )
            ):
                if chunk.text:
                    yield f"data: {chunk.text}\n\n"
        except Exception as e:
            yield f"data: [ERROR: {str(e)}]\n\n"
        finally:
            yield "data: [DONE]\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})