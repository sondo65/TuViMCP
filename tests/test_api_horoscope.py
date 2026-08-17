# -*- coding: utf-8 -*-
"""Contract tests for TuViMCP REST horoscope API."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

db_fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(db_fd)
os.environ["TUVI_DB_PATH"] = db_path


@pytest.fixture(autouse=True)
def disable_auth_for_existing_tests(monkeypatch):
    """Autouse fixture to disable auth for all existing horoscope tests."""
    monkeypatch.setenv("TUVI_MCP_AUTH_DISABLED", "1")

from tuvi_mcp.api.app import app  # noqa: E402
from tuvi_mcp.api.errors import STABLE_CODES  # noqa: E402

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


def test_generate_omits_current_year_passes_system_year():
    """POST without current_year still renders Năm xem as the system year."""
    captured = {}
    from tuvi_mcp import Horoscope

    real_render = Horoscope.render_chart

    def spy(self, chart=None, year=None, font_path=None, font_bold_path=None, locale=None, **kwargs):
        captured["year"] = year
        captured["locale"] = locale
        return real_render(self, chart, year=year, font_path=font_path, font_bold_path=font_bold_path)

    with patch.object(Horoscope, "render_chart", spy):
        response = client.post("/v1/horoscope/generate", json=VALID_PAYLOAD)

    assert response.status_code == 200
    assert captured["year"] == datetime.now().year


def test_generate_passes_explicit_current_year_to_render():
    """POST current_year is forwarded to render_chart as year."""
    captured = {}
    from tuvi_mcp import Horoscope

    real_render = Horoscope.render_chart

    def spy(self, chart=None, year=None, font_path=None, font_bold_path=None, locale=None, **kwargs):
        captured["year"] = year
        captured["locale"] = locale
        return real_render(self, chart, year=year, font_path=font_path, font_bold_path=font_bold_path)

    payload = {**VALID_PAYLOAD, "current_year": 2027}
    with patch.object(Horoscope, "render_chart", spy):
        response = client.post("/v1/horoscope/generate", json=payload)

    assert response.status_code == 200
    assert captured["year"] == 2027


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
    for field in ("name", "day", "month", "year", "hour_val", "gender_val", "is_solar", "timezone", "current_year", "locale"):
        assert field in props, f"missing D-01 field: {field}"


def test_generate_horoscope_omitted_locale_is_vi_compatible():
    """POST VALID_PAYLOAD with no locale key returns 200; captured locale is vi or None-as-vi."""
    captured = {}
    from tuvi_mcp import Horoscope

    real_render = Horoscope.render_chart

    def spy(self, chart=None, year=None, font_path=None, font_bold_path=None, locale=None, **kwargs):
        captured["locale"] = locale
        return real_render(self, chart, year=year, font_path=font_path, font_bold_path=font_bold_path)

    with patch.object(Horoscope, "render_chart", spy):
        response = client.post("/v1/horoscope/generate", json=VALID_PAYLOAD)

    assert response.status_code == 200
    assert (captured.get("locale") or "vi") == "vi"


def test_generate_horoscope_locale_en_returns_png():
    """POST locale=en returns 200 and GET image_url is still image/png."""
    payload = {**VALID_PAYLOAD, "locale": "en"}
    response = client.post("/v1/horoscope/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["image_url"].endswith(".png")
    image_response = client.get(data["image_url"])
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/png"
    assert image_response.content.startswith(b"\x89PNG")


def test_generate_horoscope_locale_en_draws_english_title():
    """POST locale=en records at least one English title draw and none equal LÁ SỐ TỬ VI."""
    from PIL import ImageDraw
    from tuvi_mcp.i18n import t

    english_title = t("en", "LÁ SỐ TỬ VI", section="ui")
    drawn = []
    real_text = ImageDraw.ImageDraw.text

    def capture(self, xy, text=None, *args, **kwargs):
        if text is not None:
            drawn.append(text)
        return real_text(self, xy, text, *args, **kwargs)

    payload = {**VALID_PAYLOAD, "locale": "en"}
    with patch.object(ImageDraw.ImageDraw, "text", capture):
        response = client.post("/v1/horoscope/generate", json=payload)

    assert response.status_code == 200
    translated_titles = (english_title, english_title.upper())
    title_draws = [s for s in drawn if s in (*translated_titles, "LÁ SỐ TỬ VI")]
    assert any(s in translated_titles for s in drawn)
    assert "LÁ SỐ TỬ VI" not in title_draws


def test_generate_horoscope_invalid_locale_fr_returns_stable_error_code():
    payload = {**VALID_PAYLOAD, "locale": "fr"}
    response = client.post("/v1/horoscope/generate", json=payload)
    assert response.status_code == 400
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert body["error"]["code"] == "INVALID_LOCALE"


def test_generate_horoscope_invalid_locale_zh_tw_returns_stable_error_code():
    payload = {**VALID_PAYLOAD, "locale": "zh-TW"}
    response = client.post("/v1/horoscope/generate", json=payload)
    assert response.status_code == 400
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert body["error"]["code"] == "INVALID_LOCALE"


def test_invalid_locale_is_stable_code():
    assert "INVALID_LOCALE" in STABLE_CODES


def pytest_sessionfinish(session, exitstatus):
    try:
        os.remove(db_path)
    except OSError:
        pass
