from fastapi import FastAPI, Header
from pydantic import BaseModel
from google import genai

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(request: ChatRequest, x_gemini_key: str = Header(...)):
    client = genai.Client(api_key=x_gemini_key)
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=request.message
    )
    return {"reply": response.text}