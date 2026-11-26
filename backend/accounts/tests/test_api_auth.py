import pytest
from jwt.exceptions import PyJWKClientConnectionError
from rest_framework.test import APIClient

from accounts import tokens

pytestmark = pytest.mark.django_db


def test_me_requires_authentication(anon):
    response = anon.get("/api/auth/me/")
    assert response.status_code == 401
    assert response["WWW-Authenticate"].startswith("Bearer")


def test_me_returns_current_user(alice):
    response = alice.client.get("/api/auth/me/")
    assert response.status_code == 200
    assert response.json()["username"] == "alice"
    assert response.json()["display_name"] == "Alicja Nowak"
    assert response.json()["keycloak_id"] == alice.sub


def test_first_request_with_valid_token_creates_local_user(make_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {make_token(username='nowy', sub='sub-nowy')}")
    response = client.get("/api/auth/me/")
    assert response.status_code == 200
    assert response.json()["username"] == "nowy"


def test_expired_token_returns_401_with_code(make_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {make_token(expires_in=-30)}")
    response = client.get("/api/auth/me/")
    assert response.status_code == 401
    assert response.json()["code"] == "token_expired"


def test_invalid_token_returns_401():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer bzdura")
    response = client.get("/api/auth/me/")
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


def test_wrong_scheme_returns_401():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Basic dXNlcjpwYXNz")
    assert client.get("/api/auth/me/").status_code == 401


def test_malformed_header_returns_401():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer a b")
    response = client.get("/api/auth/me/")
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_header"


def test_non_ascii_token_returns_401():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer caf\xe9")  # bajt 0xE9 to niepoprawny UTF-8
    response = client.get("/api/auth/me/")
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_header"


def test_keycloak_unavailable_returns_503(make_token, monkeypatch):
    def boom(token):
        raise PyJWKClientConnectionError("down")

    monkeypatch.setattr(tokens, "get_signing_key", boom)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {make_token()}")
    assert client.get("/api/auth/me/").status_code == 503


def test_auth_config_is_public(anon):
    response = anon.get("/api/auth/config/")
    assert response.status_code == 200
    body = response.json()
    assert body["client_id"] == "shopping-mobile"
    assert body["token_endpoint"].endswith("/protocol/openid-connect/token")


def test_openapi_schema_and_docs_are_public_and_describe_bearer_auth(anon):
    schema = anon.get("/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json")
    assert schema.status_code == 200
    body = schema.json()
    assert "/api/lists/" in body["paths"]
    assert body["components"]["securitySchemes"]["keycloakJWT"]["scheme"] == "bearer"
    assert anon.get("/api/docs/").status_code == 200


def test_health_ok(anon):
    response = anon.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_503_when_database_down(anon, monkeypatch):
    from django.db import connection

    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(connection, "ensure_connection", boom)
    assert anon.get("/api/health/").status_code == 503
