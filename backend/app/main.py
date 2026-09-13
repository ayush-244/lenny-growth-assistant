from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.sessions import router as sessions_router
from app.middleware import RequestIDMiddleware

app = FastAPI(
    title="The Lenny Growth Assistant",
    version="0.1.0",
    description="AI conversational assistant powered by Lenny's Podcast and Newsletter insights.",
)

app.add_middleware(RequestIDMiddleware)

# Configure CORS for local development and Docker networking
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Docker frontend service
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(sessions_router)


@app.get("/")
async def root():
    return {
        "name": "The Lenny Growth Assistant",
        "status": "running",
    }
