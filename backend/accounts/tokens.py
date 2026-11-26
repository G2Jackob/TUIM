"""Weryfikacja tokenów JWT wystawionych przez Keycloaka.

Sprawdzamy: podpis (klucz publiczny z JWKS Keycloaka), wygaśnięcie, issuer,
typ tokenu (`typ` == Bearer, żeby nie przyjąć refresh/ID tokenu) oraz klienta
(`azp`), jeśli skonfigurowano KEYCLOAK_ALLOWED_CLIENTS.
"""

import logging
from functools import lru_cache

import jwt
from django.conf import settings
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError

logger = logging.getLogger(__name__)


class TokenError(Exception):
    code = "invalid_token"
    message = "Nieprawidłowy token."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message


class InvalidToken(TokenError):
    pass


class TokenExpired(TokenError):
    code = "token_expired"
    message = "Token wygasł. Odśwież sesję."


class AuthServiceUnavailable(Exception):
    """Nie udało się pobrać kluczy z Keycloaka (np. Keycloak nie działa)."""


@lru_cache(maxsize=4)
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True, lifespan=3600, timeout=5)


def get_signing_key(token: str):
    """Zwraca klucz publiczny pasujący do `kid` z nagłówka tokenu.

    Wydzielone do osobnej funkcji, żeby w testach dało się je podmienić.
    """
    return _jwks_client(settings.KEYCLOAK_JWKS_URL).get_signing_key_from_jwt(token).key


def verify_token(token: str) -> dict:
    try:
        key = get_signing_key(token)
    except PyJWKClientConnectionError as exc:
        logger.error("Nie można pobrać JWKS z Keycloaka: %s", exc)
        raise AuthServiceUnavailable("Serwer uwierzytelniania jest niedostępny.") from exc
    except jwt.PyJWTError as exc:
        logger.warning("Odrzucono token JWT (klucz): %s: %s", type(exc).__name__, exc)
        raise InvalidToken() from exc

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=settings.KEYCLOAK_ALGORITHMS,
            issuer=settings.KEYCLOAK_ISSUER,
            leeway=settings.KEYCLOAK_LEEWAY_SECONDS,
            options={"require": ["exp", "iss", "sub"], "verify_aud": False},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpired() from exc
    except jwt.PyJWTError as exc:
        logger.warning(
            "Odrzucono token JWT: %s: %s (oczekiwany issuer: %s)",
            type(exc).__name__,
            exc,
            settings.KEYCLOAK_ISSUER,
        )
        raise InvalidToken() from exc

    if claims.get("typ", "Bearer") != "Bearer":
        raise InvalidToken("To nie jest access token.")

    allowed_clients = settings.KEYCLOAK_ALLOWED_CLIENTS
    if allowed_clients and claims.get("azp") not in allowed_clients:
        raise InvalidToken("Token został wystawiony dla innego klienta.")

    return claims