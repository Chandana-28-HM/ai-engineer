from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def home():
    return {"message": "AI Engineer Backend Running"}

@app.post("/chat")
def chat(request: ChatRequest):

    user_message = request.message

    return {
        "reply": f"Backend received: {user_message}"
    }