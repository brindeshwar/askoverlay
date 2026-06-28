from fastapi import FastAPI

app = FastAPI()

@app.post("/chat")
def chat():
    return {"message": "Hello from backend!"}
