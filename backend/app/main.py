from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {
        "message": "AI Engineer Backend Running"
    }


@app.post("/chat")
def chat():
    return {
        "response": "Hello Chandana 🚀"
    }