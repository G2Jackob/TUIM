import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from accounts import provisioning
from accounts.models import Profile
from accounts.tokens import InvalidToken

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_creates_user_and_profile_on_first_login():
    user = provisioning.get_or_create_user(
        {"sub": "s-1", "preferred_username": "ala", "email": "ala@x.pl", "given_name": "Ala"}
    )
    assert user.username == "ala"
    assert user.email == "ala@x.pl"
    assert user.first_name == "Ala"
    assert not user.has_usable_password()
    assert user.profile.keycloak_id == "s-1"


def test_second_login_returns_same_user():
    first = provisioning.get_or_create_user({"sub": "s-1", "preferred_username": "ala"})
    second = provisioning.get_or_create_user({"sub": "s-1", "preferred_username": "ala"})
    assert first.pk == second.pk
    assert User.objects.count() == 1


def test_profile_fields_are_synced_from_token():
    provisioning.get_or_create_user({"sub": "s-1", "preferred_username": "ala", "email": "old@x.pl"})
    user = provisioning.get_or_create_user(
        {"sub": "s-1", "preferred_username": "ala", "email": "new@x.pl", "family_name": "Kowalska"}
    )
    user.refresh_from_db()
    assert user.email == "new@x.pl"
    assert user.last_name == "Kowalska"


def test_missing_claims_do_not_erase_existing_data():
    provisioning.get_or_create_user({"sub": "s-1", "preferred_username": "ala", "email": "a@x.pl"})
    user = provisioning.get_or_create_user({"sub": "s-1", "preferred_username": "ala"})
    assert user.email == "a@x.pl"


def test_username_collision_gets_suffix():
    User.objects.create(username="ala")
    user = provisioning.get_or_create_user({"sub": "abcdef123456", "preferred_username": "ala"})
    assert user.username == "ala-abcdef12"


def test_falls_back_to_sub_when_no_preferred_username():
    user = provisioning.get_or_create_user({"sub": "only-sub"})
    assert user.username == "only-sub"


def test_missing_sub_is_rejected():
    with pytest.raises(InvalidToken):
        provisioning.get_or_create_user({"preferred_username": "ala"})


def test_concurrent_creation_is_handled(monkeypatch):
    existing = provisioning.get_or_create_user({"sub": "s-1", "preferred_username": "ala"})
    profile = Profile.objects.select_related("user").get(keycloak_id="s-1")
    lookups = iter([None, profile])  # pierwszy lookup: brak; po IntegrityError: jest
    monkeypatch.setattr(provisioning, "_find_profile", lambda sub: next(lookups))

    def racing_create(claims, sub):
        raise IntegrityError("duplicate key")

    monkeypatch.setattr(provisioning, "_create_user", racing_create)
    assert provisioning.get_or_create_user({"sub": "s-1"}).pk == existing.pk


def test_integrity_error_without_existing_profile_is_reraised(monkeypatch):
    monkeypatch.setattr(provisioning, "_find_profile", lambda sub: None)

    def broken_create(claims, sub):
        raise IntegrityError("coś innego")

    monkeypatch.setattr(provisioning, "_create_user", broken_create)
    with pytest.raises(IntegrityError):
        provisioning.get_or_create_user({"sub": "s-1"})
