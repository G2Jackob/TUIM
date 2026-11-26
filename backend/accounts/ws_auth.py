"""Middleware uwierzytelniające połączenia WebSocket tokenem JWT z Keycloaka.

Token może przyjść:
  1. w nagłówku `Authorization: Bearer <token>` (zalecane – OkHttp na Androidzie to potrafi),
  2. w query stringu `?token=<token>` (fallback; token trafia wtedy do logów serwera).

Wynik trafia do `scope["user"]` (User albo AnonymousUser) oraz `scope["auth_error"]`.
Samo odrzucenie połączenia robi consumer (kod zamknięcia 4401), żeby klient dostał
czytelny powód.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from .authentication import authenticate_token
from .tokens import AuthServiceUnavailable, TokenError


def extract_token(scope) -> str | None:
    headers = dict(scope.get("headers") or [])
    raw = headers.get(b"authorization")
    if raw:
        parts = raw.decode("latin-1").split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        return None
    query = parse_qs((scope.get("query_string") or b"").decode())
    values = query.get("token")
    return values[0] if values else None


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] != "websocket":
            return await self.inner(scope, receive, send)

        scope = dict(scope)
        scope["user"] = AnonymousUser()
        scope["auth_error"] = None

        token = extract_token(scope)
        if token is None:
            scope["auth_error"] = "missing_token"
        else:
            try:
                scope["user"] = await database_sync_to_async(authenticate_token)(token)
            except TokenError as exc:
                scope["auth_error"] = exc.code
            except AuthServiceUnavailable:
                scope["auth_error"] = "auth_service_unavailable"

        return await self.inner(scope, receive, send)
