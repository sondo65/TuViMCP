# -*- coding: utf-8 -*-
"""Contract tests for POST /v1/calendar and POST /v1/auspicious."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from unittest.mock import patch

db_fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(db_fd)
os.environ["TUVI_DB_PATH"] = db_path

CALENDAR_PAYLOAD = {
    "day": 22,
    "month": 8,
    "year": 2026,
    "from_solar": True,
    "timezone": 7,
}

AUSPICIOUS_PAYLOAD = {
    "day": 22,
    "month": 8,
    "year": 2026,
    "is_solar": True,
    "timezone": 7,
}


@pytest.fixture(autouse=True)
def enable_auth(monkeypatch):
    monkeypatch.delenv("TUVI_MCP_AUTH_DISABLED", raising=False)
    monkeypatch.setenv("TUVI_MCP_ENV", "test")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")


@pytest.fixture
def ec_keys():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


@pytest.fixture
def client_with_mocked_jwks(ec_keys):
    _, public_pem = ec_keys

    def mock_get_signing_key(self, token):
        from jwt import PyJWK

        public_key = serialization.load_pem_public_key(public_pem)
        public_numbers = public_key.public_numbers()

        def int_to_b64url(value, byte_length):
            return jwt.utils.base64url_encode(value.to_bytes(byte_length, "big")).decode("ascii")

        jwk_data = {
            "kty": "EC",
            "crv": "P-256",
            "x": int_to_b64url(public_numbers.x, 32),
            "y": int_to_b64url(public_numbers.y, 32),
            "use": "sig",
            "kid": "test-key-1",
            "alg": "ES256",
        }
        return PyJWK(jwk_data)

    from tuvi_mcp.api.app import app

    with patch("tuvi_mcp.api.auth.PyJWKClient.get_signing_key_from_jwt", mock_get_signing_key):
        yield TestClient(app)


def _auth_headers(private_key, claims):
    token = jwt.encode(claims, private_key, algorithm="ES256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def valid_claims():
    now = datetime.now(timezone.utc)
    return {
        "sub": "user-123",
        "role": "authenticated",
        "aud": "authenticated",
        "iss": "https://example.supabase.co/auth/v1",
        "exp": now + timedelta(hours=1),
        "iat": now,
    }


def test_calendar_no_authorization_returns_401(client_with_mocked_jwks):
    response = client_with_mocked_jwks.post("/v1/calendar", json=CALENDAR_PAYLOAD)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_auspicious_no_authorization_returns_401(client_with_mocked_jwks):
    response = client_with_mocked_jwks.post("/v1/auspicious", json=AUSPICIOUS_PAYLOAD)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_calendar_solar_to_lunar_aug_22_2026(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)

    response = client_with_mocked_jwks.post(
        "/v1/calendar", json=CALENDAR_PAYLOAD, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["lunar_day"] == 10
    assert data["lunar_month"] == 7
    assert data["lunar_year"] == 2026
    assert data["lunar_leap"] is False


def test_auspicious_aug_22_2026_fields(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)

    response = client_with_mocked_jwks.post(
        "/v1/auspicious", json=AUSPICIOUS_PAYLOAD, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "Mậu Thìn" in data["can_chi_ngay"]
    assert "Lập Thu" in data["tiet_khi_hien_tai"]
    assert "duong_lich" in data
    assert "ngay_hoang_dao" in data
    assert "gio_hoang_dao" in data
    assert isinstance(data["gio_hoang_dao"], list)
    assert "danh_gia_viec" in data
    assert data["danh_gia_viec"]["activity"] == "all"
    assert "ngu_hanh" in data
    assert "can_hanh" in data["ngu_hanh"]
    assert "quan_he_menh" not in data["ngu_hanh"]
    assert "ngay_ky" in data
    assert "pham_ky" in data["ngay_ky"]
    assert isinstance(data["ngay_ky"]["items"], list)


def test_auspicious_with_menh_includes_quan_he_menh(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)
    payload = {**AUSPICIOUS_PAYLOAD, "menh": "T"}

    response = client_with_mocked_jwks.post(
        "/v1/auspicious", json=payload, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ngu_hanh"]["menh"] == "T"
    assert "quan_he_menh" in data["ngu_hanh"]
    assert "loi_khuyen" in data["ngu_hanh"]


def test_auspicious_invalid_activity_returns_400(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)
    payload = {**AUSPICIOUS_PAYLOAD, "activity": "not_a_real_activity"}

    response = client_with_mocked_jwks.post(
        "/v1/auspicious", json=payload, headers=headers
    )

    assert response.status_code == 400


def test_auspicious_with_activity_ky_hop_dong(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)
    payload = {**AUSPICIOUS_PAYLOAD, "activity": "ky_hop_dong"}

    response = client_with_mocked_jwks.post(
        "/v1/auspicious", json=payload, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["danh_gia_viec"]["activity"] == "ky_hop_dong"
    assert "cat_percent" in data["danh_gia_viec"]


def test_auspicious_with_activity_nhap_hoc(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)
    payload = {**AUSPICIOUS_PAYLOAD, "activity": "nhap_hoc"}

    response = client_with_mocked_jwks.post(
        "/v1/auspicious", json=payload, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["danh_gia_viec"]["activity"] == "nhap_hoc"
    assert "cat_percent" in data["danh_gia_viec"]


def test_auspicious_single_day_has_no_days_key(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)

    response = client_with_mocked_jwks.post(
        "/v1/auspicious", json=AUSPICIOUS_PAYLOAD, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "days" not in data
    assert data["duong_lich"].startswith("22/08/2026")


def test_auspicious_range_returns_days_array(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)
    payload = {
        "start_day": 24,
        "start_month": 8,
        "start_year": 2026,
        "end_day": 30,
        "end_month": 8,
        "end_year": 2026,
        "is_solar": True,
        "timezone": 7,
    }

    response = client_with_mocked_jwks.post(
        "/v1/auspicious", json=payload, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert len(data["days"]) == 7
    assert data["days"][0]["duong_lich"].startswith("24/08/2026")
    assert data["days"][-1]["duong_lich"].startswith("30/08/2026")
    for day in data["days"]:
        assert "can_chi_ngay" in day
        assert "ngay_hoang_dao" in day
        assert "gio_hoang_dao" in day
        assert "danh_gia_viec" in day


def test_auspicious_range_with_activity(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)
    payload = {
        "start_day": 24,
        "start_month": 8,
        "start_year": 2026,
        "end_day": 26,
        "end_month": 8,
        "end_year": 2026,
        "activity": "ky_hop_dong",
        "is_solar": True,
        "timezone": 7,
    }

    response = client_with_mocked_jwks.post(
        "/v1/auspicious", json=payload, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["days"]) == 3
    for day in data["days"]:
        assert day["danh_gia_viec"]["activity"] == "ky_hop_dong"
        assert "cat_percent" in day["danh_gia_viec"]


def test_auspicious_range_end_before_start_returns_400(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)
    payload = {
        "start_day": 30,
        "start_month": 8,
        "start_year": 2026,
        "end_day": 24,
        "end_month": 8,
        "end_year": 2026,
        "is_solar": True,
        "timezone": 7,
    }

    response = client_with_mocked_jwks.post(
        "/v1/auspicious", json=payload, headers=headers
    )

    assert response.status_code == 400


def test_auspicious_range_too_large_returns_400(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)
    payload = {
        "start_day": 1,
        "start_month": 1,
        "start_year": 2026,
        "end_day": 15,
        "end_month": 3,
        "end_year": 2026,
        "is_solar": True,
        "timezone": 7,
    }

    response = client_with_mocked_jwks.post(
        "/v1/auspicious", json=payload, headers=headers
    )

    assert response.status_code == 400


def test_auspicious_partial_range_returns_400(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)
    payload = {
        "start_day": 24,
        "start_month": 8,
        "start_year": 2026,
        "is_solar": True,
        "timezone": 7,
    }

    response = client_with_mocked_jwks.post(
        "/v1/auspicious", json=payload, headers=headers
    )

    assert response.status_code == 400


def pytest_sessionfinish(session, exitstatus):
    try:
        os.remove(db_path)
    except OSError:
        pass
