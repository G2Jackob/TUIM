from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import APIException, AuthenticationFailed

from .provisioning import get_or_create_user
from .tokens import AuthServiceUnavailable, TokenError, verify_token


class AuthServiceUnavailableError(APIException):
    status_code = 503
    default_detail = "Serwer uwierzytelniania jest chwilowo niedostępny."
    default_code = "auth_service_unavailable"


def authenticate_token(token: str):
    """Weryfikuje token i zwraca lokalnego użytkownika (współdzielone z WebSocketami)."""
    claims = verify_token(token)
    return get_or_create_user(claims)


class KeycloakJWTAuthentication(BaseAuthentication):
    """`Authorization: Bearer <access token z Keycloaka>` → request.user (Django User)."""

    keyword = "bearer"

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != self.keyword.encode():
            return None  # brak nagłówka → DRF zwróci 401 przez permission IsAuthenticated
        if len(parts) != 2:
            raise AuthenticationFailed(
                {"detail": "Nieprawidłowy nagłówek Authorization.", "code": "invalid_header"}
            )
        try:
            token = parts[1].decode()
        except UnicodeError:
            raise AuthenticationFailed(
                {"detail": "Nieprawidłowy nagłówek Authorization.", "code": "invalid_header"}
            ) from None

        try:
            claims = verify_token(token)
            user = get_or_create_user(claims)
        except TokenError as exc:
            raise AuthenticationFailed({"detail": exc.message, "code": exc.code}) from exc
        except AuthServiceUnavailable as exc:
            raise AuthServiceUnavailableError(str(exc)) from exc
        return user, claims

    def authenticate_header(self, request):
        # obecność tego nagłówka powoduje, że brak/zły token → 401 (a nie 403)
        return 'Bearer realm="shopping"'
