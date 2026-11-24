"""Prawdziwa ścieżka pobierania kluczy z JWKS (bez podmiany `get_signing_key`).

Lokalny serwer HTTP udaje endpoint Keycloaka `/protocol/openid-connect/certs`.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from jwt.algorithms import RSAAlgorithm

from accounts import tokens
from accounts.tokens import AuthServiceUnavailable, InvalidToken, verify_token

_real_get_signing_key = tokens.get_signing_key  # zapamiętane, zanim autouse fixture je podmieni


@pytest.fixture
def jwks_server(rsa_keys, settings, monkeypatch):
    jwk = RSAAlgorithm.to_jwk(rsa_keys[1], as_dict=True)
    jwk.update({"kid": "test", "alg": "RS256", "use": "sig"})
    body = json.dumps({"keys": [jwk]}).encode()
    hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    tokens._jwks_client.cache_clear()
    settings.KEYCLOAK_JWKS_URL = f"http://127.0.0.1:{server.server_port}/certs"
    monkeypatch.setattr(tokens, "get_signing_key", _real_get_signing_key)
    yield hits
    server.shutdown()
    tokens._jwks_client.cache_clear()


def test_token_is_verified_against_keys_fetched_from_jwks(jwks_server, make_token):
    claims = verify_token(make_token(sub="real-sub"))
    assert claims["sub"] == "real-sub"
    assert len(jwks_server) == 1


def test_jwks_is_cached_between_requests(jwks_server, make_token):
    verify_token(make_token())
    verify_token(make_token())
    assert len(jwks_server) == 1


def test_token_with_unknown_kid_is_invalid(jwks_server, make_token, rsa_keys):
    import jwt

    bad = jwt.encode(
        {"sub": "x", "iss": "http://keycloak.test/realms/shopping", "exp": 9999999999},
        rsa_keys[0],
        algorithm="RS256",
        headers={"kid": "nieznany"},
    )
    with pytest.raises(InvalidToken):
        verify_token(bad)


def test_unreachable_jwks_endpoint_means_service_unavailable(settings, monkeypatch, make_token):
    tokens._jwks_client.cache_clear()
    settings.KEYCLOAK_JWKS_URL = "http://127.0.0.1:9/certs"  # nic tam nie nasłuchuje
    monkeypatch.setattr(tokens, "get_signing_key", _real_get_signing_key)
    with pytest.raises(AuthServiceUnavailable):
        verify_token(make_token())
    tokens._jwks_client.cache_clear()
