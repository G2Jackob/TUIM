from datetime import timedelta

import pytest
from django.utils import timezone

from shopping.models import ListInvite, ListMembership

pytestmark = pytest.mark.django_db


# ---- udostępnianie po e-mailu / nazwie użytkownika


def test_owner_shares_by_email(alice, bob, make_list):
    lst = make_list(alice)
    response = alice.client.post(
        f"/api/lists/{lst.id}/members/", {"identifier": "BOB@example.com"}, format="json"
    )
    assert response.status_code == 201
    assert response.json()["user"]["username"] == "bob"
    assert response.json()["role"] == "member"
    assert bob.client.get(f"/api/lists/{lst.id}/").status_code == 200


def test_owner_shares_by_username(alice, bob, make_list):
    lst = make_list(alice)
    response = alice.client.post(f"/api/lists/{lst.id}/members/", {"identifier": "bob"}, format="json")
    assert response.status_code == 201


def test_share_with_unknown_user_is_404(alice, make_list):
    lst = make_list(alice)
    response = alice.client.post(
        f"/api/lists/{lst.id}/members/", {"identifier": "nikt@example.com"}, format="json"
    )
    assert response.status_code == 404


def test_share_with_yourself_is_rejected(alice, make_list):
    lst = make_list(alice)
    response = alice.client.post(f"/api/lists/{lst.id}/members/", {"identifier": "alice"}, format="json")
    assert response.status_code == 400


def test_share_twice_conflicts(alice, bob, make_list):
    lst = make_list(alice, members=[bob])
    response = alice.client.post(f"/api/lists/{lst.id}/members/", {"identifier": "bob"}, format="json")
    assert response.status_code == 409


def test_share_requires_identifier(alice, make_list):
    lst = make_list(alice)
    assert alice.client.post(f"/api/lists/{lst.id}/members/", {}, format="json").status_code == 400
    assert alice.client.post(f"/api/lists/{lst.id}/members/", {"identifier": " "}, format="json").status_code == 400


def test_member_cannot_share(alice, bob, carol, make_list):
    lst = make_list(alice, members=[bob])
    response = bob.client.post(f"/api/lists/{lst.id}/members/", {"identifier": "carol"}, format="json")
    assert response.status_code == 403


def test_stranger_cannot_share_or_see_members(alice, carol, make_list):
    lst = make_list(alice)
    assert carol.client.post(f"/api/lists/{lst.id}/members/", {"identifier": "carol"}, format="json").status_code == 403
    assert carol.client.get(f"/api/lists/{lst.id}/members/").status_code == 403


def test_members_list_contains_owner_first(alice, bob, make_list):
    lst = make_list(alice, members=[bob])
    rows = bob.client.get(f"/api/lists/{lst.id}/members/").json()
    assert [(r["user"]["username"], r["role"]) for r in rows] == [("alice", "owner"), ("bob", "member")]


# ---- usuwanie dostępu


def test_owner_removes_member_and_member_loses_access(alice, bob, make_list):
    lst = make_list(alice, members=[bob])
    assert alice.client.delete(f"/api/lists/{lst.id}/members/{bob.user.id}/").status_code == 204
    assert bob.client.get(f"/api/lists/{lst.id}/").status_code == 403
    assert bob.client.get(f"/api/lists/{lst.id}/items/").status_code == 403


def test_member_can_leave_list(alice, bob, make_list):
    lst = make_list(alice, members=[bob])
    assert bob.client.delete(f"/api/lists/{lst.id}/members/{bob.user.id}/").status_code == 204
    assert not ListMembership.objects.filter(shopping_list=lst).exists()


def test_member_cannot_remove_someone_else(alice, bob, carol, make_list):
    lst = make_list(alice, members=[bob, carol])
    assert bob.client.delete(f"/api/lists/{lst.id}/members/{carol.user.id}/").status_code == 403


def test_remove_non_member_is_404(alice, carol, make_list):
    lst = make_list(alice)
    assert alice.client.delete(f"/api/lists/{lst.id}/members/{carol.user.id}/").status_code == 404


def test_owner_cannot_leave_own_list(alice, make_list):
    lst = make_list(alice)
    assert alice.client.delete(f"/api/lists/{lst.id}/members/{alice.user.id}/").status_code == 400


def test_stranger_cannot_remove_members(alice, bob, carol, make_list):
    lst = make_list(alice, members=[bob])
    assert carol.client.delete(f"/api/lists/{lst.id}/members/{bob.user.id}/").status_code == 403


def test_removing_member_releases_their_reservations(alice, bob, make_list, make_item):
    lst = make_list(alice, members=[bob])
    reserved = make_item(lst, "zarezerwowane", reserved_by=bob.user, reserved_at=timezone.now())
    bought = make_item(
        lst, "kupione", reserved_by=bob.user, is_purchased=True, purchased_by=bob.user
    )
    alice.client.delete(f"/api/lists/{lst.id}/members/{bob.user.id}/")
    reserved.refresh_from_db()
    bought.refresh_from_db()
    assert reserved.reserved_by is None and reserved.reserved_at is None
    assert bought.reserved_by == bob.user  # kupione zostaje nietknięte


# ---- zaproszenia


def test_owner_creates_invite_and_member_accepts(alice, bob, make_list):
    lst = make_list(alice)
    created = alice.client.post(f"/api/lists/{lst.id}/invites/")
    assert created.status_code == 201
    code = created.json()["code"]
    assert len(code) == 8

    accepted = bob.client.post("/api/invites/accept/", {"code": code.lower()}, format="json")
    assert accepted.status_code == 200
    assert accepted.json()["role"] == "member"
    assert bob.client.get(f"/api/lists/{lst.id}/").status_code == 200


def test_invite_is_single_use(alice, bob, carol, make_list):
    lst = make_list(alice)
    code = alice.client.post(f"/api/lists/{lst.id}/invites/").json()["code"]
    assert bob.client.post("/api/invites/accept/", {"code": code}, format="json").status_code == 200
    assert carol.client.post("/api/invites/accept/", {"code": code}, format="json").status_code == 410


def test_expired_invite_is_gone(alice, bob, make_list):
    lst = make_list(alice)
    code = alice.client.post(f"/api/lists/{lst.id}/invites/").json()["code"]
    ListInvite.objects.filter(code=code).update(expires_at=timezone.now() - timedelta(minutes=1))
    assert bob.client.post("/api/invites/accept/", {"code": code}, format="json").status_code == 410
    assert not ListMembership.objects.exists()


def test_unknown_invite_code_is_404(bob):
    assert bob.client.post("/api/invites/accept/", {"code": "NIEMA123"}, format="json").status_code == 404


def test_accept_requires_code(bob):
    assert bob.client.post("/api/invites/accept/", {}, format="json").status_code == 400


def test_owner_cannot_accept_own_invite(alice, make_list):
    lst = make_list(alice)
    code = alice.client.post(f"/api/lists/{lst.id}/invites/").json()["code"]
    assert alice.client.post("/api/invites/accept/", {"code": code}, format="json").status_code == 400


def test_existing_member_accepting_invite_conflicts_and_keeps_code_unused(alice, bob, make_list):
    lst = make_list(alice, members=[bob])
    code = alice.client.post(f"/api/lists/{lst.id}/invites/").json()["code"]
    assert bob.client.post("/api/invites/accept/", {"code": code}, format="json").status_code == 409
    assert ListInvite.objects.get(code=code).used_at is None


def test_only_owner_can_create_invites(alice, bob, carol, make_list):
    lst = make_list(alice, members=[bob])
    assert bob.client.post(f"/api/lists/{lst.id}/invites/").status_code == 403
    assert carol.client.post(f"/api/lists/{lst.id}/invites/").status_code == 403


def test_accept_invite_requires_auth(anon):
    assert anon.post("/api/invites/accept/", {"code": "X"}, format="json").status_code == 401
