"""Local JWT auth for the Docker/local-dev environment (two seeded roles:
admin, employee). In the hosted deployment this route is bypassed entirely
and the frontend talks to Supabase Auth directly — see docs/DEPLOYMENT.md.
Everything downstream only depends on the decoded JWT claims, so nothing
else in the backend changes when that swap happens.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = create_access_token(subject=user.id, role=user.role, email=user.email)
    return LoginResponse(access_token=token, user=UserOut.model_validate(user, from_attributes=True))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user, from_attributes=True)
