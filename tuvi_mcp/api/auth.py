# -*- coding: utf-8 -*-
"""JWT authentication for TuViMCP FastAPI endpoints."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional
from urllib.error import URLError
from urllib.request import urlopen
import json

from fastapi import Header
import jwt
from jwt import PyJWKClient


logger = logging.getLogger(__name__)

_ALLOWED_ALGS = ["ES256", "RS256"]


class UnauthorizedError(Exception):
    """Custom exception for authentication failures."""
    
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient:
    """Get cached PyJWKClient for JWKS endpoint."""
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    if not supabase_url:
        raise UnauthorizedError("Missing SUPABASE_URL configuration")
    
    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url, cache_keys=True, max_cached_keys=10)


def _is_auth_disabled() -> bool:
    """Check if JWT auth is disabled based on environment settings."""
    # Production environment never skips auth
    env = os.getenv("TUVI_MCP_ENV", "").lower()
    if env == "production":
        return False
    
    # Non-production: check disable flag
    disabled = os.getenv("TUVI_MCP_AUTH_DISABLED", "").lower()
    return disabled in {"1", "true", "yes"}


@dataclass(frozen=True)
class AuthStartupStatus:
    auth_enabled: bool
    supabase_url: str
    warnings: list[str]
    fatal_error: Optional[str] = None


def auth_status_for_startup() -> AuthStartupStatus:
    """Summarize auth configuration for process startup."""
    warnings: list[str] = []
    env = os.getenv("TUVI_MCP_ENV", "").lower()
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    auth_disabled = _is_auth_disabled()

    if env == "production" and not supabase_url:
        return AuthStartupStatus(
            auth_enabled=True,
            supabase_url="",
            warnings=warnings,
            fatal_error="TUVI_MCP_ENV=production requires SUPABASE_URL for JWT verification",
        )

    if auth_disabled:
        warnings.append(
            "TUVI_MCP_AUTH_DISABLED is set — JWT verification skipped for POST /v1/horoscope/*"
        )
        return AuthStartupStatus(
            auth_enabled=False,
            supabase_url=supabase_url,
            warnings=warnings,
        )

    if not supabase_url:
        warnings.append(
            "SUPABASE_URL is missing — POST /v1/horoscope/* will return 401 until configured"
        )

    return AuthStartupStatus(
        auth_enabled=True,
        supabase_url=supabase_url,
        warnings=warnings,
    )


def probe_jwks_key_count() -> int:
    """Return number of keys in Supabase JWKS, or 0 when unreachable."""
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    if not supabase_url:
        return 0

    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    try:
        with urlopen(jwks_url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        keys = payload.get("keys", [])
        return len(keys) if isinstance(keys, list) else 0
    except (URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return 0


def require_supabase_jwt(authorization: Optional[str] = Header(default=None)) -> dict:
    """
    FastAPI dependency that verifies Supabase JWT tokens.
    
    Returns decoded JWT claims if valid, raises UnauthorizedError if invalid.
    """
    # Check if auth is disabled (per-request check, not cached)
    if _is_auth_disabled():
        logger.debug("JWT auth bypassed via TUVI_MCP_AUTH_DISABLED")
        # Return mock claims for disabled auth
        return {
            "sub": "auth-disabled-user",
            "role": "authenticated", 
            "aud": "authenticated",
            "iss": "disabled",
        }
    
    # Extract Bearer token
    if not authorization:
        raise UnauthorizedError("Missing bearer token")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedError("Invalid authorization header format")
    
    token = parts[1]
    
    try:
        # Get JWKS client and signing key
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Verify JWT with strict validation
        supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        issuer = f"{supabase_url}/auth/v1"
        
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=_ALLOWED_ALGS,
            audience="authenticated",
            issuer=issuer,
            leeway=30,
            options={
                "require": ["exp", "sub", "role", "aud", "iss"],
            }
        )
        
        # Additional role validation
        if claims.get("role") != "authenticated":
            raise UnauthorizedError("Invalid role claim")
        
        return claims
        
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid token")
    except UnauthorizedError:
        raise
    except Exception:
        # Catch JWKS / network errors from PyJWKClient
        raise UnauthorizedError("Token verification failed")
