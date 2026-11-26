"""Wspólne fixtury testów: fałszywy Keycloak (klucz RSA), użytkownicy, klienci API."""

import time
import uuid
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts import provisioning, tokens
from shopping import events
from shopping.models import Item, ListMembership, ShoppingList

ISSUER = "http://keycloak.test/realms/shopping"


@pytest.fixture(scope="session")
def rsa_keys():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private, private.public_key()


@pytest.fixture(autouse=True)
def _test_environment(settings, monkeypatch, rsa_keys):
    settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "tests"}
    }
    settings.KEYCLOAK_ISSUER = ISSUER
    settings.KEYCLOAK_ALLOWED_CLIENTS = ["shopping-mobile"]
    settings.KEYCLOAK_ALGORITHMS = ["RS256"]
    settings.KEYCLOAK_LEEWAY_SECONDS = 0
    settings.EXCHANGE_API_BASE_URL = "http://fx.test/api"
    settings.EXCHANGE_API_TIMEOUT = 1
    settings.EXCHANGE_RATE_CACHE_TTL = 60
    settings.INVITE_TTL_HOURS = 48
    cache.clear()
    # zamiast pobierać JWKS z Keycloaka, używamy klucza publicznego z testu
    monkeypatch.setattr(tokens, "get_signing_key", lambda token: rsa_keys[1])
    # callbacki on_commit wykonują się od razu (testy bez transaction=True)
    monkeypatch.setattr(events, "_after_commit", lambda fn: fn())


@pytest.fixture
def make_token(rsa_keys):
    def _make(
        sub=None,
        username="user",
        email=None,
        expires_in=300,
        issuer=ISSUER,
        azp="shopping-mobile",
        typ="Bearer",
        key=None,
        omit=(),
        **extra,
    ):
        now = int(time.time())
        claims = {
            "sub": sub or str(uuid.uuid4()),
            "iss": issuer,
            "iat": now,
            "exp": now + expires_in,
            "typ": typ,
            "azp": azp,
            "preferred_username": username,
            "email": email if email is not None else f"{username}@example.com",
            **extra,
        }
        for name in omit:
            claims.pop(name, None)
        return jwt.encode(claims, key or rsa_keys[0], algorithm="RS256", headers={"kid": "test"})

    return _make


@pytest.fixture
def make_actor(db, make_token):
    """Tworzy użytkownika (tak jak przy pierwszym logowaniu) + token + klienta API."""

    def _make(username, **claims):
        sub = str(uuid.uuid4())
        user = provisioning.get_or_create_user(
            {"sub": sub, "preferred_username": username, "email": f"{username}@example.com", **claims}
        )
        token = make_token(sub=sub, username=username)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return SimpleNamespace(user=user, token=token, client=client, sub=sub)

    return _make


@pytest.fixture
def alice(make_actor):
    return make_actor("alice", given_name="Alicja", family_name="Nowak")


@pytest.fixture
def bob(make_actor):
    return make_actor("bob")


@pytest.fixture
def carol(make_actor):
    return make_actor("carol")


@pytest.fixture
def anon():
    return APIClient()


@pytest.fixture
def make_list(db):
    def _make(owner, name="Zakupy", members=(), **fields):
        lst = ShoppingList.objects.create(owner=owner.user, name=name, **fields)
        for member in members:
            ListMembership.objects.create(shopping_list=lst, user=member.user)
        return lst

    return _make


@pytest.fixture
def make_item(db):
    def _make(lst, name="Mleko", **fields):
        return Item.objects.create(shopping_list=lst, name=name, **fields)

    return _make


@pytest.fixture
def published(monkeypatch):
    """Zapisuje zdarzenia WebSocket zamiast wysyłać je do warstwy kanałów."""
    sent = []
    monkeypatch.setattr(events, "_send", lambda group, payload: sent.append((group, payload)))
    return sent
