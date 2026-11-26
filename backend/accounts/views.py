from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeSerializer


class MeView(APIView):
    """Dane zalogowanego użytkownika (przydatne do sprawdzenia, czy token działa)."""

    @extend_schema(responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user).data)


class AuthConfigView(APIView):
    """Publiczna konfiguracja Keycloaka dla aplikacji mobilnej (np. dla AppAuth).

    Rejestracja i logowanie odbywają się w Keycloaku (Authorization Code + PKCE),
    backend tylko weryfikuje otrzymane tokeny.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(responses=dict)
    def get(self, request):
        issuer = settings.KEYCLOAK_ISSUER.rstrip("/")
        oidc = f"{issuer}/protocol/openid-connect"
        return Response(
            {
                "issuer": issuer,
                "client_id": settings.KEYCLOAK_MOBILE_CLIENT_ID,
                "authorization_endpoint": f"{oidc}/auth",
                "token_endpoint": f"{oidc}/token",
                "registration_endpoint": f"{oidc}/registrations",
                "end_session_endpoint": f"{oidc}/logout",
                "jwks_uri": f"{oidc}/certs",
            }
        )
