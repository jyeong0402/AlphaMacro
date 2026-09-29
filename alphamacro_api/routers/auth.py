"""Authentication endpoints under /api/v1/auth."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from ..core.security import hash_password, verify_password, create_access_token
router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(409, "Email already registered")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    return TokenResponse(access_token=create_access_token(str(user.id)))
