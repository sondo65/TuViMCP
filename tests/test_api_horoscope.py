# -*- coding: utf-8 -*-
"""Contract tests for TuViMCP REST horoscope API."""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

db_fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(db_fd)
os.environ["TUVI_DB_PATH"] = db_path

from tuvi_mcp.api.app import app  # noqa: E402

client = TestClient(app)

VALID_PAYLOAD = {
    "name": "Nguyễn Văn A",
    "day": 10,
    "month": 6,
    "year": 1995,
    "hour_val": "14:30",
    "gender_val": "Nam",
    "is_solar": True,
    "timezone": 7,
}


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_horoscope_valid_payload_returns_image_url_and_name():
    response = client.post("/v1/horoscope/generate", json=VALID_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    
    # Verify response shape
    assert "image_url" in data
    assert "name" in data
    assert data["name"] == "Nguyễn Văn A"
    
    # Verify image_url is relative path
    assert data["image_url"].startswith("/v1/horoscope/images/")
    assert data["image_url"].endswith(".png")
    assert not data["image_url"].startswith("http://127.0.0.1")
    
    # Test that GET image endpoint works
    image_response = client.get(data["image_url"])
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/png"
    
    # Verify PNG content (magic bytes)
    content = image_response.content
    assert len(content) > 1000  # Reasonable size check
    assert content.startswith(b'\x89PNG')  # PNG magic bytes


def test_generate_horoscope_invalid_date_returns_stable_error_code():
    payload = {**VALID_PAYLOAD, "month": 13, "day": 32}
    response = client.post("/v1/horoscope/generate", json=payload)
    assert response.status_code in (400, 422)
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert body["error"]["code"] == "INVALID_BIRTH_DATE"
    assert body["error"]["code"] != "INVALID_INPUT_PARAMETER"


def test_get_chart_image_unknown_id_returns_404_with_error_code():
    """GET unknown chart ID returns 404 with CHART_IMAGE_NOT_FOUND error code."""
    response = client.get("/v1/horoscope/images/unknown-id.png")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert "error" in body["detail"]
    assert "code" in body["detail"]["error"]
    assert body["detail"]["error"]["code"] == "CHART_IMAGE_NOT_FOUND"


def test_get_chart_image_invalid_uuid_blocked():
    """GET with invalid UUID format is blocked."""
    response = client.get("/v1/horoscope/images/invalid-uuid-format.png")
    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["error"]["code"] == "CHART_IMAGE_NOT_FOUND"


def test_generate_horoscope_request_uses_d01_field_names():
    """OpenAPI body must expose D-01 field names (hour_val, gender_val, is_solar)."""
    openapi = app.openapi()
    schema = (
        openapi["components"]["schemas"].get("HoroscopeGenerateRequest")
        or openapi["paths"]["/v1/horoscope/generate"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    )
    if "$ref" in schema:
        schema = openapi["components"]["schemas"][schema["$ref"].split("/")[-1]]
    props = schema.get("properties", schema)
    for field in ("name", "day", "month", "year", "hour_val", "gender_val", "is_solar", "timezone"):
        assert field in props, f"missing D-01 field: {field}"


def pytest_sessionfinish(session, exitstatus):
    try:
        os.remove(db_path)
    except OSError:
        pass
