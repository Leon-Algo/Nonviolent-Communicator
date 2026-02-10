from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.health import router as health_router
from app.api.routers.progress import router as progress_router
from app.api.routers.reflections import router as reflections_router
from app.api.routers.scenes import router as scenes_router
from app.api.routers.sessions import router as sessions_router
from app.core.config import settings

app = FastAPI(
    title="NVC Practice Coach API",
    version="0.1.0",
    description="FastAPI backend for NVC Practice Coach MVP",
)

origins = [item.strip() for item in settings.cors_origins.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(scenes_router)
app.include_router(sessions_router)
app.include_router(reflections_router)
app.include_router(progress_router)
