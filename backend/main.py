from fastapi import FastAPI, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(request: ChatRequest, x_gemini_key: str = Header(...)):
    client = genai.Client(api_key=x_gemini_key)
    
    def generate():
        for chunk in client.models.generate_content_stream(
            model="gemini-3.5-flash",
            contents=request.message
        ):
            if chunk.text:
                yield f"data: {chunk.text}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")