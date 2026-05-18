from __future__ import annotations

from typing import Any, Optional

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import crud
from app.config import settings
from app.database import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def _require_supabase_config() -> tuple[str, str]:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase auth is enabled but SUPABASE_URL or SUPABASE_ANON_KEY is missing",
        )
    return settings.supabase_url.rstrip("/"), settings.supabase_anon_key


def _fetch_supabase_user(token: str) -> dict[str, Any]:
    supabase_url, anon_key = _require_supabase_config()
    try:
        response = requests.get(
            f"{supabase_url}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": anon_key,
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not verify auth session",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired auth session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return response.json()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not settings.enable_auth:
        return crud.get_or_create_default_user(db)

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to use RecallBox",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supabase_user = _fetch_supabase_user(credentials.credentials)
    subject = supabase_user.get("id")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return crud.get_or_create_auth_user(
        db,
        provider="supabase",
        subject=str(subject),
        email=supabase_user.get("email"),
    )
