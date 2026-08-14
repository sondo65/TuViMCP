# -*- coding: utf-8 -*-
"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tuvi_mcp.api.routes import health, horoscope

app = FastAPI(title="TuViMCP REST")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(horoscope.router)
