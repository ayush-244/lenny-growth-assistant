from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(
    title="The Lenny Growth Assistant",
    version="0.1.0",
    description="AI conversational assistant powered by Lenny's Podcast and Newsletter insights.",
)

app.include_router(health_router)


@app.get("/")
async def root():
    return {
        "name": "The Lenny Growth Assistant",
        "status": "running",
    }
