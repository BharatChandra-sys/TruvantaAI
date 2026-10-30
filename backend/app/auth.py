# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: TruvantaAI � https://github.com/BharatChandra-sys/fake-news-extension
"""
Authentication utilities
JWT token generation and validation for user authentication.
"""

import os
from jose import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from app.models import User

# JWT configuration
# Read from JWT_SECRET (canonical name used in .env and deployment dashboards).
# Fail fast at startup if missing — never silently use an insecure default.
SECRET_KEY = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET environment variable is required. "
        "Generate one with: openssl rand -hex 32"
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)  # Don't raise error if no token


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token"""
    token = credentials.credentials
    payload = decode_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


# The signed token already proves who is calling. Confirming that the account
# still exists costs several database round trips (~220 ms from Render to
# Neon), so on the hot path it is confirmed at most once per user per window.
_USER_CONFIRM_TTL_S = 300
_confirmed_users: dict = {}


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """The caller's user id, for routes that need only the id (the live check)."""
    import time
    payload = decode_token(credentials.credentials)
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    now = time.monotonic()
    if _confirmed_users.get(user_id, 0) > now:
        return user_id
    from database import SessionLocal
    db = SessionLocal()
    try:
        exists = db.query(User.id).filter(User.id == user_id).first() is not None
    finally:
        db.close()
    if not exists:
        _confirmed_users.pop(user_id, None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if len(_confirmed_users) > 10000:
        _confirmed_users.clear()
    _confirmed_users[user_id] = now + _USER_CONFIRM_TTL_S
    return user_id


async def get_current_user_ws(token: str, db: Session = None) -> User:
    """
    Get the current authenticated user from JWT token for WebSocket connections.
    
    This is a separate function because WebSocket connections can't use Depends().
    """
    from database import SessionLocal
    
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        payload = decode_token(token)
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
    
    finally:
        if close_db:
            db.close()


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get the current user if authenticated, otherwise return None (allows anonymous access)"""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = decode_token(token)
        
        user_id = payload.get("sub")
        if user_id is None:
            return None
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        return user
    except Exception:
        return None



# Password hashing
import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_token(user_id: int) -> str:
    """Create a JWT token for a user"""
    return create_access_token(data={"sub": str(user_id)})


# Google OAuth verification
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


def verify_google_token(token: str) -> dict:
    """Verify a Google ID token and return user info"""
    try:
        # Specify the CLIENT_ID of the app that accesses the backend
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured"
            )
        
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            client_id
        )
        
        # ID token is valid. Get the user's Google Account ID from the decoded token.
        return {
            "email": idinfo.get("email"),
            "name": idinfo.get("name", ""),
            "google_id": idinfo.get("sub"),
            "picture": idinfo.get("picture", "")
        }
    except ValueError as e:
        # Invalid token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )


def verify_google_access_token(access_token: str) -> dict:
    """Verify a Google access token and return user info."""
    import requests as http_requests

    try:
        # Use params dict — never put tokens in URL strings (logged by proxies)
        response = http_requests.get(
            "https://www.googleapis.com/oauth2/v1/tokeninfo",
            params={"access_token": access_token},
            timeout=10,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google access token",
            )

        token_info = response.json()

        # Validate audience — ensure token was issued for OUR app
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        if client_id and token_info.get("audience") != client_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token was not issued for this application",
            )

        # Get user info using Authorization header (not URL param)
        user_response = http_requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not fetch user info",
            )

        user_info = user_response.json()

        return {
            "email":     user_info.get("email"),
            "name":      user_info.get("name", ""),
            "google_id": user_info.get("id"),
            "picture":   user_info.get("picture", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google access token: {str(e)}",
        )
