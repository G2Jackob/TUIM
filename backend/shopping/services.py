"""Logika biznesowa: dostęp do list, członkowie, zaproszenia, rezerwacje, sumy.

Widoki są cienkie – wszystkie reguły (i gałęzie warunkowe do przetestowania)
siedzą tutaj. Operacje na pozycjach blokują wiersz (`select_for_update`), więc
dwóch użytkowników klikających „Ja to kupuję” w tej samej chwili nie
zarezerwuje tej samej pozycji (wygra jeden, drugi dostanie 409).
"""

import secrets
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from . import fx
from .exceptions import ConflictError, GoneError
from .models import Item, ListInvite, ListMembership, ShoppingList

User = get_user_model()

INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # bez mylących znaków 0/O/1/I
INVITE_LENGTH = 8


# ---------------------------------------------------------------- dostęp


def access_filter(user_id: int) -> Q:
    """Listy, do których użytkownik ma dostęp (własne + udostępnione)."""
    shared = ListMembership.objects.filter(user_id=user_id).values("shopping_list_id")
    return Q(owner_id=user_id) | Q(pk__in=shared)


def has_access(user, lst: ShoppingList) -> bool:
    if lst.owner_id == user.id:
        return True
    return ListMembership.objects.filter(shopping_list=lst, user=user).exists()


def is_owner(user, lst: ShoppingList) -> bool:
    return lst.owner_id == user.id


def has_list_access_by_id(user_id: int, list_id) -> bool:
    return ShoppingList.objects.filter(pk=list_id).filter(access_filter(user_id)).exists()


def ensure_writable(lst: ShoppingList) -> None:
    if lst.is_archived:
        raise ConflictError("Lista jest zarchiwizowana – przywróć ją, aby wprowadzać zmiany.")


def lists_with_counts():
    return ShoppingList.objects.select_related("owner").annotate(
        items_count=Count("items", distinct=True),
        purchased_count=Count("items", filter=Q(items__is_purchased=True), distinct=True),
    )


def set_archived(lst: ShoppingList, value: bool) -> ShoppingList:
    if lst.is_archived != value:
        lst.is_archived = value
        lst.save(update_fields=["is_archived", "updated_at"])
    return lst


# ---------------------------------------------------------------- członkowie


def find_user_by_identifier(identifier: str):
    identifier = identifier.strip()
    return (
        User.objects.filter(Q(email__iexact=identifier) | Q(username__iexact=identifier))
        .order_by("id")
        .first()
    )


def add_member(lst: ShoppingList, identifier: str):
    target = find_user_by_identifier(identifier)
    if target is None:
        raise NotFound(
            "Nie znaleziono użytkownika. Osoba musi najpierw zalogować się do aplikacji."
        )
    if target.id == lst.owner_id:
        raise ValidationError({"identifier": ["Właściciel ma już pełny dostęp do tej listy."]})
    membership, created = ListMembership.objects.get_or_create(shopping_list=lst, user=target)
    if not created:
        raise ConflictError("Ten użytkownik ma już dostęp do tej listy.")
    return target, membership


def remove_member(lst: ShoppingList, actor, user_id: int) -> list:
    """Usuwa członka (właściciel – dowolnego, członek – tylko siebie).

    Zwraca id pozycji, których rezerwacja została zwolniona.
    """
    if user_id == lst.owner_id:
        raise ValidationError("Właściciel nie może opuścić listy – może ją usunąć.")
    if actor.id != lst.owner_id and actor.id != user_id:
        raise PermissionDenied("Możesz usunąć dostęp tylko sobie.")

    with transaction.atomic():
        membership = ListMembership.objects.filter(shopping_list=lst, user_id=user_id).first()
        if membership is None:
            raise NotFound("Ten użytkownik nie jest członkiem listy.")
        reserved = Item.objects.filter(
            shopping_list=lst, reserved_by_id=user_id, is_purchased=False
        )
        released_ids = list(reserved.values_list("id", flat=True))
        reserved.update(reserved_by=None, reserved_at=None, updated_at=timezone.now())
        membership.delete()
    return released_ids


# ---------------------------------------------------------------- zaproszenia


def _new_code() -> str:
    while True:
        code = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(INVITE_LENGTH))
        if not ListInvite.objects.filter(code=code).exists():
            return code


def create_invite(lst: ShoppingList, user) -> ListInvite:
    return ListInvite.objects.create(
        shopping_list=lst,
        code=_new_code(),
        created_by=user,
        expires_at=timezone.now() + timedelta(hours=settings.INVITE_TTL_HOURS),
    )


def accept_invite(code: str, user) -> ShoppingList:
    with transaction.atomic():
        invite = (
            ListInvite.objects.select_for_update(of=("self",))
            .select_related("shopping_list")
            .filter(code=code.strip().upper())
            .first()
        )
        if invite is None:
            raise NotFound("Nieprawidłowy kod zaproszenia.")
        if invite.used_at is not None:
            raise GoneError("Ten kod zaproszenia został już wykorzystany.")
        if invite.expires_at <= timezone.now():
            raise GoneError("Ten kod zaproszenia wygasł.")

        lst = invite.shopping_list
        if lst.owner_id == user.id:
            raise ValidationError("Jesteś właścicielem tej listy.")
        if ListMembership.objects.filter(shopping_list=lst, user=user).exists():
            raise ConflictError("Masz już dostęp do tej listy.")

        ListMembership.objects.create(shopping_list=lst, user=user)
        invite.used_by = user
        invite.used_at = timezone.now()
        invite.save(update_fields=["used_by", "used_at"])
    return lst


# ---------------------------------------------------------------- rezerwacje


def _lock_item(item_id) -> Item:
    # `of=("self",)` – Postgres nie pozwala blokować strony nullable outer joina
    item = Item.objects.select_for_update(of=("self",)).get(pk=item_id)
    return item


def _save(item: Item, *fields: str) -> None:
    item.save(update_fields=[*fields, "updated_at"])


def reserve_item(item_id, user) -> Item:
    with transaction.atomic():
        item = _lock_item(item_id)
        ensure_writable(item.shopping_list)
        if item.is_purchased:
            raise ConflictError("Ten produkt został już kupiony.")
        if item.reserved_by_id is not None:
            if item.reserved_by_id == user.id:
                return item  # idempotentnie: już zarezerwowane przez Ciebie
            raise ConflictError("Ten produkt jest już zarezerwowany przez inną osobę.")
        item.reserved_by = user
        item.reserved_at = timezone.now()
        _save(item, "reserved_by", "reserved_at")
    return item


def release_item(item_id, user) -> Item:
    with transaction.atomic():
        item = _lock_item(item_id)
        lst = item.shopping_list
        ensure_writable(lst)
        if item.is_purchased:
            raise ConflictError("Produkt jest oznaczony jako kupiony – najpierw cofnij zakup.")
        if item.reserved_by_id is None:
            raise ConflictError("Ten produkt nie jest zarezerwowany.")
        if item.reserved_by_id != user.id and not is_owner(user, lst):
            raise PermissionDenied("Rezerwację może zwolnić tylko osoba, która ją zrobiła, lub właściciel listy.")
        item.reserved_by = None
        item.reserved_at = None
        _save(item, "reserved_by", "reserved_at")
    return item


def purchase_item(item_id, user) -> Item:
    with transaction.atomic():
        item = _lock_item(item_id)
        ensure_writable(item.shopping_list)
        if item.is_purchased:
            if item.purchased_by_id == user.id:
                return item  # idempotentnie
            raise ConflictError("Ten produkt został już kupiony przez inną osobę.")
        if item.reserved_by_id is not None and item.reserved_by_id != user.id:
            raise ConflictError("Ten produkt jest zarezerwowany przez inną osobę.")
        item.is_purchased = True
        item.purchased_by = user
        item.purchased_at = timezone.now()
        _save(item, "is_purchased", "purchased_by", "purchased_at")
    return item


def unpurchase_item(item_id, user) -> Item:
    with transaction.atomic():
        item = _lock_item(item_id)
        lst = item.shopping_list
        ensure_writable(lst)
        if not item.is_purchased:
            raise ConflictError("Ten produkt nie jest oznaczony jako kupiony.")
        if item.purchased_by_id != user.id and not is_owner(user, lst):
            raise PermissionDenied("Zakup może cofnąć tylko osoba, która go oznaczyła, lub właściciel listy.")
        item.is_purchased = False
        item.purchased_by = None
        item.purchased_at = None
        _save(item, "is_purchased", "purchased_by", "purchased_at")
    return item


# ---------------------------------------------------------------- sumy + waluty

MONEY_QUANT = Decimal("0.01")


def list_total(lst: ShoppingList, target_currency: str | None = None) -> dict:
    """Suma szacunkowa listy (cena jednostkowa × ilość) i opcjonalne przeliczenie walut."""
    priced = lst.items.filter(estimated_price__isnull=False)
    total = priced.aggregate(
        total=Sum(
            ExpressionWrapper(
                F("estimated_price") * F("quantity"),
                output_field=DecimalField(max_digits=20, decimal_places=5),
            )
        )
    )["total"] or Decimal("0")
    total = Decimal(total).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    # kwoty i kursy jako stringi (jak w serializerach) – bez utraty precyzji w JSON-ie
    result = {
        "list_id": str(lst.id),
        "currency": lst.currency,
        "total": str(total),
        "items_priced": priced.count(),
        "items_without_price": lst.items.filter(estimated_price__isnull=True).count(),
        "converted": None,
    }
    if target_currency:
        rate = fx.get_rate(lst.currency, target_currency)
        converted = (total * rate.rate).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        result["converted"] = {
            "currency": target_currency,
            "total": str(converted),
            "rate": str(rate.rate),
            "rate_date": rate.date,
            "stale": rate.stale,
        }
    return result
