import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import get_settings
from src.database.connection import create_db_and_tables
from src.utils.logging_config import setup_logging
from src.api.routes import chat, admin, health, appointments, auth

setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Healthcare Symptom Triage API",
    description="AI-powered symptom triage and hospital routing system",
    version="1.0.0",
)

# CORS — allow React dev server + admin frontend
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
    _seed_default_admin()
    from src.mcp.client import get_mcp_client
    await get_mcp_client().start()


@app.on_event("shutdown")
async def on_shutdown():
    from src.mcp.client import get_mcp_client
    await get_mcp_client().stop()


def _seed_default_admin():
    """Create the default admin account if no nurse users exist yet."""
    import bcrypt
    from src.database.repository import count_nurse_users, create_nurse_user

    if count_nurse_users() > 0:
        return

    password_hash = bcrypt.hashpw(b"Admin@123", bcrypt.gensalt()).decode()
    create_nurse_user(
        email="admin@cityhospital.com",
        password_hash=password_hash,
        full_name="System Admin",
        department=None,   # null = all departments
        role="admin",
    )
    logger.info("Default admin user seeded — email: admin@cityhospital.com  password: Admin@123")


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(chat.router,         prefix="/api/v1", tags=["Triage Chat"])
app.include_router(admin.router,        prefix="/api/v1", tags=["Admin"])
app.include_router(appointments.router, prefix="/api/v1", tags=["Appointments"])
app.include_router(auth.router,         prefix="/api/v1", tags=["Auth"])
app.include_router(health.router, tags=["Health"])
