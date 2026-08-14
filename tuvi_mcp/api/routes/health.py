# -*- coding: utf-8 -*-
"""Health check route."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    """Smoke-test endpoint for dev and CI."""
    return {"status": "ok"}
