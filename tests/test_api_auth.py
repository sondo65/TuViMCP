# -*- coding: utf-8 -*-
"""JWT auth contract tests for TuViMCP FastAPI endpoints."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
import jwt

# Create temporary database for test isolation
db_fd, db_path = tempfile.mkstemp(suffix=".db")
os.close(db_fd)
os.environ["TUVI_DB_PATH"] = db_path


@pytest.fixture(autouse=True)
def enable_auth_for_auth_tests(monkeypatch):
    """Enable auth for auth tests by removing AUTH_DISABLED and setting test env."""
    monkeypatch.delenv("TUVI_MCP_AUTH_DISABLED", raising=False)
    monkeypatch.setenv("TUVI_MCP_ENV", "test")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")


@pytest.fixture
def ec_keys():
    """Generate EC keypair for ES256 JWT testing."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem, public_pem


@pytest.fixture
def mock_jwks(ec_keys):
    """Mock JWKS response with test EC public key."""
    _, public_pem = ec_keys
    
    # Convert PEM to JWK format for ES256
    public_key = serialization.load_pem_public_key(public_pem)
    public_numbers = public_key.public_numbers()
    
    # Convert coordinates to base64url
    def int_to_b64url(value, byte_length):
        return jwt.utils.base64url_encode(value.to_bytes(byte_length, 'big'))
    
    x = int_to_b64url(public_numbers.x, 32)
    y = int_to_b64url(public_numbers.y, 32)
    
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "x": x.decode('ascii'),
        "y": y.decode('ascii'),
        "use": "sig",
        "kid": "test-key-1",
        "alg": "ES256"
    }
    
    return {"keys": [jwk]}


@pytest.fixture
def client_with_mocked_jwks(mock_jwks, ec_keys):
    """Test client with mocked JWKS endpoint."""
    
    def mock_get_signing_key(self, token):
        """Mock PyJWKClient.get_signing_key_from_jwt to return test key."""
        _, public_pem = ec_keys
        from jwt import PyJWK
        from cryptography.hazmat.primitives import serialization
        import jwt.utils
        
        # Load the public key from PEM  
        public_key = serialization.load_pem_public_key(public_pem)
        public_numbers = public_key.public_numbers()
        
        # Convert to JWK format for ES256
        def int_to_b64url(value, byte_length):
            return jwt.utils.base64url_encode(value.to_bytes(byte_length, 'big')).decode('ascii')
        
        x = int_to_b64url(public_numbers.x, 32)
        y = int_to_b64url(public_numbers.y, 32)
        
        jwk_data = {
            "kty": "EC",
            "crv": "P-256",
            "x": x,
            "y": y,
            "use": "sig",
            "kid": "test-key-1",
            "alg": "ES256"
        }
        
        return PyJWK(jwk_data)
    
    # Import app after env is set up
    from tuvi_mcp.api.app import app
    
    # Mock PyJWKClient methods that auth.py uses
    with patch("tuvi_mcp.api.auth.PyJWKClient.get_signing_key_from_jwt", mock_get_signing_key):
        yield TestClient(app)


def create_jwt_token(private_key, claims):
    """Create JWT token with given claims using ES256."""
    return jwt.encode(claims, private_key, algorithm="ES256")


@pytest.fixture
def valid_jwt_claims():
    """Valid JWT claims for authenticated user."""
    now = datetime.now(timezone.utc)
    return {
        "sub": "user-123",
        "role": "authenticated", 
        "aud": "authenticated",
        "iss": "https://example.supabase.co/auth/v1",
        "exp": now + timedelta(hours=1),
        "iat": now,
    }


def test_generate_no_authorization_returns_401(client_with_mocked_jwks):
    """POST /generate with no Authorization header returns 401 UNAUTHORIZED."""
    payload = {
        "name": "Test User",
        "day": 10,
        "month": 6,
        "year": 1995,
        "hour_val": "14:30",
        "gender_val": "Nam",
        "is_solar": True,
        "timezone": 7,
    }
    
    response = client_with_mocked_jwks.post("/v1/horoscope/generate", json=payload)
    
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert "WWW-Authenticate" in response.headers
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_generate_missing_supabase_url_returns_config_detail(client_with_mocked_jwks, monkeypatch):
    """Missing SUPABASE_URL must not be swallowed as Token verification failed."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    from tuvi_mcp.api.auth import _get_jwks_client

    _get_jwks_client.cache_clear()
    payload = {
        "name": "Test User",
        "day": 10,
        "month": 6,
        "year": 1995,
        "hour_val": "14:30",
        "gender_val": "Nam",
        "is_solar": True,
        "timezone": 7,
    }
    headers = {"Authorization": "Bearer abc.def.ghi"}

    response = client_with_mocked_jwks.post(
        "/v1/horoscope/generate", json=payload, headers=headers
    )

    assert response.status_code == 401
    assert response.json()["error"]["detail"] == "Missing SUPABASE_URL configuration"


def test_generate_garbage_token_returns_401(client_with_mocked_jwks):
    """POST with Bearer garbage token returns 401 UNAUTHORIZED."""
    payload = {
        "name": "Test User", 
        "day": 10,
        "month": 6,
        "year": 1995,
        "hour_val": "14:30",
        "gender_val": "Nam",
        "is_solar": True,
        "timezone": 7,
    }
    headers = {"Authorization": "Bearer abc.def.ghi"}
    
    response = client_with_mocked_jwks.post("/v1/horoscope/generate", json=payload, headers=headers)
    
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_generate_hs256_token_returns_401(client_with_mocked_jwks, valid_jwt_claims):
    """POST with HS256 JWT signed with random secret returns 401 (HS256 not allowed)."""
    # Create HS256 token with random secret
    hs256_token = jwt.encode(valid_jwt_claims, "random-secret", algorithm="HS256")
    
    payload = {
        "name": "Test User",
        "day": 10,
        "month": 6,
        "year": 1995,
        "hour_val": "14:30",
        "gender_val": "Nam",
        "is_solar": True,
        "timezone": 7,
    }
    headers = {"Authorization": f"Bearer {hs256_token}"}
    
    response = client_with_mocked_jwks.post("/v1/horoscope/generate", json=payload, headers=headers)
    
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_generate_expired_token_returns_401(client_with_mocked_jwks, ec_keys):
    """POST with ES256 token whose exp is in the past returns 401."""
    private_key, _ = ec_keys
    
    # Create expired token (exp in the past)
    now = datetime.now(timezone.utc)
    expired_claims = {
        "sub": "user-123",
        "role": "authenticated",
        "aud": "authenticated", 
        "iss": "https://example.supabase.co/auth/v1",
        "exp": now - timedelta(hours=1),  # Expired
        "iat": now - timedelta(hours=2),
    }
    
    token = create_jwt_token(private_key, expired_claims)
    
    payload = {
        "name": "Test User",
        "day": 10,
        "month": 6,
        "year": 1995,
        "hour_val": "14:30",
        "gender_val": "Nam", 
        "is_solar": True,
        "timezone": 7,
    }
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client_with_mocked_jwks.post("/v1/horoscope/generate", json=payload, headers=headers)
    
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_generate_anon_aud_returns_401(client_with_mocked_jwks, ec_keys):
    """POST with ES256 token aud=anon returns 401."""
    private_key, _ = ec_keys
    
    now = datetime.now(timezone.utc)
    anon_claims = {
        "sub": "user-123",
        "role": "anon",  # Not authenticated
        "aud": "anon",   # Not authenticated
        "iss": "https://example.supabase.co/auth/v1",
        "exp": now + timedelta(hours=1),
        "iat": now,
    }
    
    token = create_jwt_token(private_key, anon_claims)
    
    payload = {
        "name": "Test User",
        "day": 10,
        "month": 6,
        "year": 1995,
        "hour_val": "14:30",
        "gender_val": "Nam",
        "is_solar": True,
        "timezone": 7,
    }
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client_with_mocked_jwks.post("/v1/horoscope/generate", json=payload, headers=headers)
    
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_generate_anon_role_returns_401(client_with_mocked_jwks, ec_keys):
    """POST with ES256 token role=anon returns 401."""
    private_key, _ = ec_keys
    
    now = datetime.now(timezone.utc)
    anon_role_claims = {
        "sub": "user-123",
        "role": "anon",  # Not authenticated
        "aud": "authenticated",
        "iss": "https://example.supabase.co/auth/v1",
        "exp": now + timedelta(hours=1),
        "iat": now,
    }
    
    token = create_jwt_token(private_key, anon_role_claims)
    
    payload = {
        "name": "Test User",
        "day": 10,
        "month": 6,
        "year": 1995,
        "hour_val": "14:30",
        "gender_val": "Nam",
        "is_solar": True,
        "timezone": 7,
    }
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client_with_mocked_jwks.post("/v1/horoscope/generate", json=payload, headers=headers)
    
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_generate_valid_token_returns_200(client_with_mocked_jwks, ec_keys, valid_jwt_claims):
    """POST with valid ES256 token (aud=authenticated, role=authenticated) returns 200."""
    private_key, _ = ec_keys
    
    token = create_jwt_token(private_key, valid_jwt_claims)
    
    payload = {
        "name": "Test User",
        "day": 10,
        "month": 6,
        "year": 1995,
        "hour_val": "14:30",
        "gender_val": "Nam",
        "is_solar": True,
        "timezone": 7,
    }
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client_with_mocked_jwks.post("/v1/horoscope/generate", json=payload, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "image_base64" in data
    assert "name" in data


def test_generate_anonymous_user_token_returns_200(client_with_mocked_jwks, ec_keys):
    """POST with authenticated role + is_anonymous true returns 200 (guest user)."""
    private_key, _ = ec_keys
    
    now = datetime.now(timezone.utc)
    guest_claims = {
        "sub": "user-123",
        "role": "authenticated",
        "aud": "authenticated", 
        "iss": "https://example.supabase.co/auth/v1",
        "exp": now + timedelta(hours=1),
        "iat": now,
        "is_anonymous": True,  # Guest user
    }
    
    token = create_jwt_token(private_key, guest_claims)
    
    payload = {
        "name": "Guest User",
        "day": 10, 
        "month": 6,
        "year": 1995,
        "hour_val": "14:30",
        "gender_val": "Nam",
        "is_solar": True,
        "timezone": 7,
    }
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client_with_mocked_jwks.post("/v1/horoscope/generate", json=payload, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "image_base64" in data
    assert "name" in data


def test_health_no_header_returns_200(client_with_mocked_jwks):
    """GET /health with no header returns 200 (public endpoint)."""
    response = client_with_mocked_jwks.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_images_route_gone(client_with_mocked_jwks):
    """GET /v1/horoscope/images is removed; no JWT required path remains."""
    response = client_with_mocked_jwks.get("/v1/horoscope/images/test-uuid.png")
    assert response.status_code == 404


def pytest_sessionfinish(session, exitstatus):
    """Clean up temporary database."""
    try:
        os.remove(db_path)
    except OSError:
        pass