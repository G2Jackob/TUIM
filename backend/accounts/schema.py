from drf_spectacular.extensions import OpenApiAuthenticationExtension


class KeycloakJWTScheme(OpenApiAuthenticationExtension):
    """Pokazuje w Swaggerze przycisk „Authorize” (Bearer JWT z Keycloaka)."""

    target_class = "accounts.authentication.KeycloakJWTAuthentication"
    name = "keycloakJWT"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
