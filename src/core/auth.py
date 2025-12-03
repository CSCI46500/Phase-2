"""
Authentication and authorization module.
Implements user registration, login, and token validation as per CRUD_IMPLEMENTATION_PLAN.md
"""
import secrets
import hashlib
import bcrypt
import json
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, Header, Depends
import logging

from src.core.models import User, Token
from src.core.database import get_db
from src.core.config import settings

logger = logging.getLogger(__name__)


def hash_password(password: str, salt: str) -> str:
    """Hash password with salt using bcrypt."""
    combined = (password + salt).encode()
    # Bcrypt has a 72-byte limit, truncate if necessary
    if len(combined) > 72:
        combined = combined[:72]
    return bcrypt.hashpw(combined, bcrypt.gensalt()).decode()


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    """Verify password against stored hash."""
    combined = (password + salt).encode()
    # Bcrypt has a 72-byte limit, truncate if necessary (must match hash_password)
    if len(combined) > 72:
        combined = combined[:72]
    try:
        return bcrypt.checkpw(combined, password_hash.encode())
    except Exception as e:
        logger.warning(f"Password verification failed: {e}")
        return False


def create_user(
    db: Session,
    username: str,
    password: str,
    permissions: List[str],
    is_admin: bool = False
) -> User:
    """
    Create a new user with hashed password.
    As per CRUD plan: Admin-initiated user registration.
    """
    # Check if user already exists
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Generate salt and hash password
    salt = secrets.token_hex(16)
    password_hash = hash_password(password, salt)

    # Create user
    user = User(
        username=username,
        password_hash=password_hash,
        salt=salt,
        is_admin=is_admin,
        permissions=permissions
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"Created user: {username} (admin={is_admin})")
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticate user with username and password.
    Returns User if valid, None otherwise.
    """
    user = db.query(User).filter(User.username == username).first()

    if not user:
        logger.warning(f"Login attempt for non-existent user: {username}")
        return None

    if not verify_password(password, user.salt, user.password_hash):
        logger.warning(f"Invalid password for user: {username}")
        return None

    logger.info(f"User authenticated: {username}")
    return user


def generate_token(db: Session, user: User) -> str:
    """
    Generate API token for user.
    As per CRUD plan: JWT-like token valid for 1000 API calls.
    """
    # Generate random token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Calculate expiry
    expires_at = datetime.now() + timedelta(days=settings.token_expiry_days)

    # Store token in database
    db_token = Token(
        user_id=user.id,
        token_hash=token_hash,
        api_calls_remaining=settings.default_api_calls,
        expires_at=expires_at
    )

    db.add(db_token)
    db.commit()

    logger.info(f"Generated token for user: {user.username}")
    return token


def verify_token(db: Session, token: str) -> Optional[User]:
    """
    Verify API token and return associated user.
    Decrements API call counter.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Find token in database
    db_token = db.query(Token).filter(Token.token_hash == token_hash).first()

    if not db_token:
        logger.warning("Invalid token provided")
        return None

    # Check expiry
    if db_token.expires_at and datetime.now() > db_token.expires_at:
        logger.warning(f"Expired token for user_id: {db_token.user_id}")
        return None

    # Check remaining calls
    if db_token.api_calls_remaining <= 0:
        logger.warning(f"No API calls remaining for token (user_id: {db_token.user_id})")
        return None

    # Decrement call counter
    db_token.api_calls_remaining -= 1
    db.commit()

    # Get user
    user = db.query(User).filter(User.id == db_token.user_id).first()

    if not user:
        logger.error(f"Token exists but user not found: {db_token.user_id}")
        return None

    return user


def check_permission(user: User, required_permission: str) -> bool:
    """
    Check if user has required permission.
    Permissions: 'upload', 'download', 'search', 'admin'
    """
    if user.is_admin:
        return True

    permissions = user.permissions if isinstance(user.permissions, list) else []
    return required_permission in permissions


# FastAPI dependencies for authentication
async def get_current_user(
    x_auth_token: str = Header(..., alias="X-Authorization"),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user from token.
    Usage: user: User = Depends(get_current_user)
    """
    user = verify_token(db, x_auth_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def require_permission(permission: str):
    """
    FastAPI dependency factory to require specific permission.
    Usage: user: User = Depends(require_permission('upload'))
    """
    async def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not check_permission(user, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Missing required permission: {permission}"
            )
        return user
    return permission_checker


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency to require admin privileges.
    Usage: admin: User = Depends(require_admin)
    """
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin permission required")
    return user


def init_default_admin(db: Session):
    """
    Initialize default admin user if not exists.
    Called on application startup.
    """
    admin = db.query(User).filter(User.username == settings.admin_username).first()

    if not admin:
        logger.info("Creating default admin user...")
        create_user(
            db=db,
            username=settings.admin_username,
            password=settings.admin_password,
            permissions=["upload", "download", "search", "admin"],
            is_admin=True
        )
        logger.info("Default admin user created")
    else:
        logger.info("Default admin user already exists")