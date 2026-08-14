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


def test_generate_horoscope_valid_payload_shape():
    response = client.post("/v1/horoscope/generate", json=VALID_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert "thien_ban" in data
    assert "dia_ban" in data
    assert "cach_cuc" in data
    assert isinstance(data["dia_ban"], list)
    assert len(data["dia_ban"]) == 12
    assert data["thien_ban"]["ten"] == "Nguyễn Văn A"


def test_generate_horoscope_invalid_date_returns_stable_error_code():
    payload = {**VALID_PAYLOAD, "month": 13, "day": 32}
    response = client.post("/v1/horoscope/generate", json=payload)
    assert response.status_code in (400, 422)
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert body["error"]["code"] == "INVALID_BIRTH_DATE"
    assert body["error"]["code"] != "INVALID_INPUT_PARAMETER"


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
