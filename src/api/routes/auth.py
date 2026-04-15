"""
Authentication routes — login and current-user lookup.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
import bcrypt
from jose import jwt

from src.config.settings import get_settings
from src.database.repository import get_nurse_by_email
from src.api.dependencies import get_current_user
from src.models.db_models import NurseUser

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    department: str | None
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_token(user: NurseUser) -> str:
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user.id,
        "email": user.email,
        "department": user.department,
        "role": user.role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate a nurse/admin and return a JWT token."""
    user = get_nurse_by_email(request.email)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not bcrypt.checkpw(request.password.encode(), user.password_hash.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = _create_token(user)
    return LoginResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            department=user.department,
            role=user.role,
        ),
    )


@router.get("/auth/me", response_model=UserOut)
async def get_me(current_user: NurseUser = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        department=current_user.department,
        role=current_user.role,
    )
