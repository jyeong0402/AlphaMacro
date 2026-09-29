"""JWT authentication and password hashing utilities."""
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from ..database import get_db
from ..core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(subject: str) -> str:
    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": subject, "exp": expiry}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def user_from_token(token: str, db: Session):
    """Resolve a bearer token for HTTP and WebSocket authentication."""
    from ..models.user import User

    try:
        subject = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]).get("sub")
        user_id = int(subject)
    except (JWTError, TypeError, ValueError):
        return None
    user = db.get(User, user_id)
    return user if user and user.is_active else None


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]):
    credentials = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials",
                                headers={"WWW-Authenticate": "Bearer"})
    user = user_from_token(token, db)
    if not user:
        raise credentials
    return user
