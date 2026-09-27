"""Password hashing + JWT issuance/verification.

This is the local-dev/Docker `AuthProvider`. In the hosted deployment this
module is swapped for Supabase Auth (which issues its own JWTs verified the
same way against Supabase's JWKS) — see docs/DEPLOYMENT.md. Everything
downstream (routes, RBAC) only depends on the decoded `{sub, role, email}`
claims, not on how they were issued, so the swap touches this file alone.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: str, email: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
