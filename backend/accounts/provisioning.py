"""Tworzenie / aktualizacja lokalnego użytkownika na podstawie claimów z JWT."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from .models import Profile
from .tokens import InvalidToken

User = get_user_model()

_SYNCED_FIELDS = (("email", "email"), ("first_name", "given_name"), ("last_name", "family_name"))


def _find_profile(sub: str):
    return Profile.objects.select_related("user").filter(keycloak_id=sub).first()


def _unique_username(preferred: str | None, sub: str) -> str:
    base = (preferred or sub)[:150]
    if not User.objects.filter(username__iexact=base).exists():
        return base
    return f"{base[:140]}-{sub[:8]}"


def _create_user(claims: dict, sub: str):
    with transaction.atomic():
        user = User(
            username=_unique_username(claims.get("preferred_username"), sub),
            email=(claims.get("email") or "")[:254],
            first_name=(claims.get("given_name") or "")[:150],
            last_name=(claims.get("family_name") or "")[:150],
        )
        user.set_unusable_password()
        user.save()
        Profile.objects.create(user=user, keycloak_id=sub)
    return user


def _sync_fields(user, claims: dict) -> None:
    changed = []
    for field, claim in _SYNCED_FIELDS:
        value = claims.get(claim) or ""
        if value and getattr(user, field) != value:
            setattr(user, field, value)
            changed.append(field)
    if changed:
        user.save(update_fields=changed)


def get_or_create_user(claims: dict):
    sub = claims.get("sub")
    if not sub:
        raise InvalidToken("Brak identyfikatora użytkownika w tokenie.")
    sub = str(sub)

    profile = _find_profile(sub)
    if profile is None:
        try:
            return _create_user(claims, sub)
        except IntegrityError:
            # równoległe żądanie utworzyło tego samego użytkownika
            profile = _find_profile(sub)
            if profile is None:
                raise

    _sync_fields(profile.user, claims)
    return profile.user
