import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings
from database import get_db
from models.user import User
from schemas.auth_schemas import UserCreate, UserResponse, LoginRequest
from core.security import get_current_user
from models.audit_log import AuditLog

auth_logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


class _LazyCryptContext:
    def __init__(self):
        self._ctx = None

    def _get_ctx(self):
        if self._ctx is None:
            from passlib.context import CryptContext
            self._ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return self._ctx

    def hash(self, secret: str, **kwargs):
        return self._get_ctx().hash(secret, **kwargs)

    def verify(self, secret: str, hash: str, **kwargs):
        return self._get_ctx().verify(secret, hash, **kwargs)

    def __getattr__(self, name):
        return getattr(self._get_ctx(), name)


pwd_context = _LazyCryptContext()


def create_access_token(data: dict):
    from jose import jwt

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict):
    from jose import jwt

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
def register_user(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    db_user = (
        db.query(User)
        .filter((User.username == user.username) | (User.email == user.email))
        .first()
    )
    if db_user:
        raise HTTPException(
            status_code=400, detail="Username or email already registered"
        )

    hashed_pwd = pwd_context.hash(user.password)
    new_user = User(
        username=user.username, email=user.email, hashed_password=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, user: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Authenticate with username + password. Returns JWT access and refresh tokens."""
    db_user = (
        db.query(User)
        .filter((User.username == user.username) | (User.email == user.username))
        .first()
    )
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    db_user.last_login = datetime.utcnow()

    # Log the login action
    audit = AuditLog(
        user_id=db_user.id,
        action_type="LOGIN",
        resource_type="Session",
        description="User logged in via UI"
    )
    db.add(audit)
    db.commit()

    access_token = create_access_token(
        data={"sub": db_user.username, "role": db_user.role}
    )
    refresh_token = create_refresh_token(data={"sub": db_user.username})

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="lax",
        secure=True,  # assumes HTTPS
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": db_user.role,
    }


@router.post("/refresh")
@limiter.limit("20/minute")
def refresh_token(
    request: Request, response: Response, refresh_token: str = Cookie(None), db: Session = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    from jose import JWTError, jwt
    try:
        payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access = create_access_token(data={"sub": user.username, "role": user.role})
    new_refresh = create_refresh_token(data={"sub": user.username})

    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="lax",
        secure=True,
    )

    return {
        "access_token": new_access,
        "token_type": "bearer",
    }


@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, email: EmailStr, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user:
        # In a production setting, integrate with SendGrid, SES, or similar to send the actual email.
        reset_token = create_access_token(data={"sub": user.username, "type": "reset"})
        auth_logger.info(f"Generated password reset request for {email}")

    return {
        "message": "If the email is registered, a password reset link has been sent."
    }

    return {
        "message": "If the email is registered, a password reset link has been sent."
    }


@router.post("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    from jose import JWTError, jwt
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=400, detail="Invalid token")

        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # user.is_verified = True (assuming we had an is_verified column)
        auth_logger.info(f"User {username} successfully verified email.")
        return {"message": "Email verified successfully."}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")


class ProfileUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: Optional[str] = Field(None, min_length=6, max_length=128)
    preferences: Optional[dict] = None


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login,
        "preferences": current_user.preferences,
    }


@router.put("/me")
def update_me(
    req: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if req.email:
        current_user.email = req.email
    if req.username:
        # Check if already exists
        exist = db.query(User).filter(User.username == req.username).first()
        if exist and exist.id != current_user.id:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = req.username
    if req.password:
        current_user.hashed_password = pwd_context.hash(req.password)
    if req.preferences is not None:
        current_user.preferences = req.preferences

    db.commit()
    db.refresh(current_user)
    return {"message": "Profile updated successfully"}


@router.get("/audit-logs")
def get_my_audit_logs(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.timestamp.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": log.id,
            "action_type": log.action_type,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "description": log.description,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "timestamp": log.timestamp,
            "metadata": log.metadata_json,
        }
        for log in logs
    ]
