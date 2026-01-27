"""
Authentication utilities for login system
"""
from fastapi import HTTPException, Depends, Cookie
from starlette.requests import Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import Optional
import secrets

from server.core.database import get_db
from server.core.db_models import User

# Simple session storage (in production, use Redis or database sessions)
active_sessions = {}

security = HTTPBearer(auto_error=False)


def create_session(user_id: int, username: str) -> str:
    """Create a new session and return session token"""
    session_token = secrets.token_urlsafe(32)
    active_sessions[session_token] = {
        "user_id": user_id,
        "username": username
    }
    return session_token


def get_session(session_token: Optional[str] = None) -> Optional[dict]:
    """Get session data from token"""
    if not session_token:
        return None
    return active_sessions.get(session_token)


def delete_session(session_token: str):
    """Delete a session"""
    if session_token in active_sessions:
        del active_sessions[session_token]


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current authenticated user from session"""
    # Get session token from cookies
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        return None
    
    session_data = get_session(session_token)
    if not session_data:
        return None
    
    user = db.query(User).filter(User.id == session_data["user_id"]).first()
    return user


def require_auth(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Dependency to require authentication"""
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    return current_user
