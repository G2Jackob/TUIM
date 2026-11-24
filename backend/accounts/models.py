from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Łączy lokalnego użytkownika Django z kontem w Keycloaku (claim `sub`).

    Użytkownik lokalny jest tworzony automatycznie przy pierwszym poprawnym
    żądaniu z tokenem JWT, dzięki czemu modele aplikacji mogą mieć zwykłe
    klucze obce do `auth.User`.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    keycloak_id = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user} ({self.keycloak_id})"
