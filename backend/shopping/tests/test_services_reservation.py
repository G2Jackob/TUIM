"""Testy jednostkowe reguł rezerwacji / zakupu – każda gałąź warunków."""

import pytest
from rest_framework.exceptions import PermissionDenied

from shopping import services
from shopping.exceptions import ConflictError

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(alice, bob, carol, make_list, make_item):
    lst = make_list(alice, members=[bob, carol])
    item = make_item(lst)
    return lst, item


# ---- reserve


def test_reserve_free_item(setup, bob):
    _, item = setup
    result = services.reserve_item(item.pk, bob.user)
    assert result.reserved_by == bob.user
    assert result.reserved_at is not None


def test_reserve_is_idempotent_for_same_user(setup, bob):
    _, item = setup
    services.reserve_item(item.pk, bob.user)
    again = services.reserve_item(item.pk, bob.user)
    assert again.reserved_by == bob.user


def test_reserve_blocked_when_taken_by_someone_else(setup, bob, carol):
    _, item = setup
    services.reserve_item(item.pk, bob.user)
    with pytest.raises(ConflictError) as exc:
        services.reserve_item(item.pk, carol.user)
    assert "zarezerwowany" in str(exc.value.detail)


def test_reserve_purchased_item_conflicts(setup, bob):
    _, item = setup
    services.purchase_item(item.pk, bob.user)
    with pytest.raises(ConflictError):
        services.reserve_item(item.pk, bob.user)


def test_reserve_on_archived_list_conflicts(setup, bob):
    lst, item = setup
    services.set_archived(lst, True)
    with pytest.raises(ConflictError) as exc:
        services.reserve_item(item.pk, bob.user)
    assert "zarchiwizowana" in str(exc.value.detail)


# ---- release


def test_release_by_reserver(setup, bob):
    _, item = setup
    services.reserve_item(item.pk, bob.user)
    result = services.release_item(item.pk, bob.user)
    assert result.reserved_by is None and result.reserved_at is None


def test_release_by_list_owner_is_allowed(setup, alice, bob):
    _, item = setup
    services.reserve_item(item.pk, bob.user)
    assert services.release_item(item.pk, alice.user).reserved_by is None


def test_release_by_other_member_is_forbidden(setup, bob, carol):
    _, item = setup
    services.reserve_item(item.pk, bob.user)
    with pytest.raises(PermissionDenied):
        services.release_item(item.pk, carol.user)


def test_release_not_reserved_conflicts(setup, bob):
    _, item = setup
    with pytest.raises(ConflictError):
        services.release_item(item.pk, bob.user)


def test_release_purchased_item_conflicts(setup, bob):
    _, item = setup
    services.reserve_item(item.pk, bob.user)
    services.purchase_item(item.pk, bob.user)
    with pytest.raises(ConflictError):
        services.release_item(item.pk, bob.user)


# ---- purchase


def test_purchase_free_item(setup, bob):
    _, item = setup
    result = services.purchase_item(item.pk, bob.user)
    assert result.is_purchased and result.purchased_by == bob.user and result.purchased_at


def test_purchase_own_reservation(setup, bob):
    _, item = setup
    services.reserve_item(item.pk, bob.user)
    assert services.purchase_item(item.pk, bob.user).is_purchased


def test_purchase_blocked_when_reserved_by_someone_else(setup, bob, carol):
    _, item = setup
    services.reserve_item(item.pk, bob.user)
    with pytest.raises(ConflictError):
        services.purchase_item(item.pk, carol.user)


def test_purchase_twice_by_same_user_is_idempotent(setup, bob):
    _, item = setup
    services.purchase_item(item.pk, bob.user)
    assert services.purchase_item(item.pk, bob.user).purchased_by == bob.user


def test_purchase_already_bought_by_someone_else_conflicts(setup, bob, carol):
    _, item = setup
    services.purchase_item(item.pk, bob.user)
    with pytest.raises(ConflictError):
        services.purchase_item(item.pk, carol.user)


# ---- unpurchase


def test_unpurchase_by_buyer(setup, bob):
    _, item = setup
    services.purchase_item(item.pk, bob.user)
    result = services.unpurchase_item(item.pk, bob.user)
    assert not result.is_purchased and result.purchased_by is None and result.purchased_at is None


def test_unpurchase_by_owner_is_allowed(setup, alice, bob):
    _, item = setup
    services.purchase_item(item.pk, bob.user)
    assert not services.unpurchase_item(item.pk, alice.user).is_purchased


def test_unpurchase_by_other_member_is_forbidden(setup, bob, carol):
    _, item = setup
    services.purchase_item(item.pk, bob.user)
    with pytest.raises(PermissionDenied):
        services.unpurchase_item(item.pk, carol.user)


def test_unpurchase_not_purchased_conflicts(setup, bob):
    _, item = setup
    with pytest.raises(ConflictError):
        services.unpurchase_item(item.pk, bob.user)


def test_unpurchase_keeps_reservation(setup, bob):
    _, item = setup
    services.reserve_item(item.pk, bob.user)
    services.purchase_item(item.pk, bob.user)
    assert services.unpurchase_item(item.pk, bob.user).reserved_by == bob.user
