import logging
from datetime import datetime, timedelta, timezone
from typing import Dict
from fastapi import Request, HTTPException
import jwt

from autoapply.env import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS

logger = logging.getLogger(__name__)


def create_jwt(email: str) -> str:
    """Create a JWT token for the given email."""
    payload = {
        "sub": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_jwt(token: str) -> Dict[str, str]:
    """Decode and verify a JWT token, returning the payload."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(request: Request) -> str:
    """
    FastAPI dependency to extract and verify the current user from the request cookie.
    Returns the user's email if authenticated.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_jwt(token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return email
