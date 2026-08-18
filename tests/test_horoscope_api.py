# -*- coding: utf-8 -*-
"""Contract tests for POST /chart and POST /transit JSON endpoints."""

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

TRANSIT_PAYLOAD = {
    **VALID_PAYLOAD,
    "current_year": 2026,
    "current_month": 5,
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


def test_chart_no_authorization_returns_401(client_with_mocked_jwks):
    response = client_with_mocked_jwks.post("/v1/horoscope/chart", json=VALID_PAYLOAD)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_transit_no_authorization_returns_401(client_with_mocked_jwks):
    response = client_with_mocked_jwks.post("/v1/horoscope/transit", json=TRANSIT_PAYLOAD)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_chart_valid_token_returns_dia_ban_thien_ban(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)

    response = client_with_mocked_jwks.post(
        "/v1/horoscope/chart", json=VALID_PAYLOAD, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "dia_ban" in data
    assert "thien_ban" in data
    assert len(data["dia_ban"]) == 12


def test_transit_valid_token_returns_target_year(
    client_with_mocked_jwks, ec_keys, valid_claims
):
    private_key, _ = ec_keys
    headers = _auth_headers(private_key, valid_claims)

    response = client_with_mocked_jwks.post(
        "/v1/horoscope/transit", json=TRANSIT_PAYLOAD, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["target_period"]["current_year"] == 2026
    assert "dai_han" in data
    assert "tieu_han" in data
    assert "nguyet_han" in data


def pytest_sessionfinish(session, exitstatus):
    try:
        os.remove(db_path)
    except OSError:
        pass
