from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import get_settings
from src.database.connection import create_db_and_tables
from src.utils.logging_config import setup_logging
from src.api.routes import chat, admin, health

setup_logging()

settings = get_settings()

app = FastAPI(
    title="Healthcare Symptom Triage API",
    description="AI-powered symptom triage and hospital routing system",
    version="1.0.0",
)

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    create_db_and_tables()


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(chat.router, prefix="/api/v1", tags=["Triage Chat"])
app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])
app.include_router(health.router, tags=["Health"])
