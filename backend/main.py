from fastapi import FastAPI

app = FastAPI()

@app.post("/chat")
def chat():
    return {"reply": "Hello from backend!"}
