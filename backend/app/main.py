from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.routers import agent, chat, conversations, projects, repos

app = FastAPI(title=settings.app_name, version="1.0.0", debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


@app.get("/")
async def home():
    return {
        "message": "AI Engineer Backend Running",
        "provider": settings.configured_provider,
        "model": settings.llm_model,
        "docs": "/docs",
    }


app.include_router(projects.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(repos.router)
app.include_router(agent.router)
