import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from accounts import tokens
from accounts.tokens import AuthServiceUnavailable, InvalidToken, TokenExpired, verify_token


def test_valid_token_returns_claims(make_token):
    claims = verify_token(make_token(sub="abc", username="ala"))
    assert claims["sub"] == "abc"
    assert claims["preferred_username"] == "ala"


def test_expired_token(make_token):
    with pytest.raises(TokenExpired) as exc:
        verify_token(make_token(expires_in=-60))
    assert exc.value.code == "token_expired"


def test_token_signed_with_other_key_is_rejected(make_token):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(InvalidToken):
        verify_token(make_token(key=other_key))


def test_wrong_issuer_is_rejected(make_token):
    with pytest.raises(InvalidToken):
        verify_token(make_token(issuer="http://evil.test/realms/shopping"))


def test_garbage_token_is_rejected():
    with pytest.raises(InvalidToken):
        verify_token("to-nie-jest-jwt")


def test_token_without_sub_is_rejected(make_token):
    with pytest.raises(InvalidToken):
        verify_token(make_token(omit=("sub",)))


def test_refresh_token_is_not_accepted_as_access_token(make_token):
    with pytest.raises(InvalidToken) as exc:
        verify_token(make_token(typ="Refresh"))
    assert "access token" in exc.value.message


def test_token_for_other_client_is_rejected(make_token):
    with pytest.raises(InvalidToken):
        verify_token(make_token(azp="other-client"))


def test_client_check_is_skipped_when_allowed_clients_empty(make_token, settings):
    settings.KEYCLOAK_ALLOWED_CLIENTS = []
    assert verify_token(make_token(azp="whatever"))["azp"] == "whatever"


def test_missing_azp_is_rejected_when_clients_configured(make_token):
    with pytest.raises(InvalidToken):
        verify_token(make_token(omit=("azp",)))


def test_unknown_kid_is_invalid_token(make_token, monkeypatch):
    def boom(token):
        raise PyJWKClientError("Unable to find a signing key")

    monkeypatch.setattr(tokens, "get_signing_key", boom)
    with pytest.raises(InvalidToken):
        verify_token(make_token())


def test_keycloak_down_raises_service_unavailable(make_token, monkeypatch):
    def boom(token):
        raise PyJWKClientConnectionError("connection refused")

    monkeypatch.setattr(tokens, "get_signing_key", boom)
    with pytest.raises(AuthServiceUnavailable):
        verify_token(make_token())
