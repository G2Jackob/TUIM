import uuid

import pytest

pytestmark = pytest.mark.django_db


def test_all_endpoints_require_authentication(anon, alice, make_list):
    lst = make_list(alice)
    assert anon.get("/api/lists/").status_code == 401
    assert anon.post("/api/lists/", {"name": "x"}, format="json").status_code == 401
    assert anon.get(f"/api/lists/{lst.id}/").status_code == 401
    assert anon.get(f"/api/lists/{lst.id}/items/").status_code == 401


# ---- tworzenie


def test_create_list(alice):
    response = alice.client.post(
        "/api/lists/", {"name": "  Weekend  ", "description": "grill", "currency": "eur"}, format="json"
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Weekend"
    assert body["currency"] == "EUR"
    assert body["role"] == "owner"
    assert body["owner"]["username"] == "alice"
    assert body["items_count"] == 0
    assert body["is_archived"] is False


def test_create_list_uses_default_currency(alice):
    response = alice.client.post("/api/lists/", {"name": "Domowa"}, format="json")
    assert response.status_code == 201
    assert response.json()["currency"] == "PLN"


@pytest.mark.parametrize("name", ["", "   "])
def test_create_list_rejects_blank_name(alice, name):
    response = alice.client.post("/api/lists/", {"name": name}, format="json")
    assert response.status_code == 400
    assert response.json()["name"] == ["Nazwa listy nie może być pusta."]


def test_create_list_requires_name(alice):
    response = alice.client.post("/api/lists/", {}, format="json")
    assert response.status_code == 400
    assert "name" in response.json()


@pytest.mark.parametrize("currency", ["EURO", "e1", "12", ""])
def test_create_list_rejects_bad_currency(alice, currency):
    response = alice.client.post("/api/lists/", {"name": "X", "currency": currency}, format="json")
    assert response.status_code == 400
    assert "currency" in response.json()


def test_client_cannot_set_owner_or_archived_flag(alice, bob):
    response = alice.client.post(
        "/api/lists/", {"name": "X", "owner": bob.user.id, "is_archived": True}, format="json"
    )
    assert response.status_code == 201
    assert response.json()["owner"]["id"] == alice.user.id
    assert response.json()["is_archived"] is False


# ---- odczyt


def test_list_shows_own_and_shared_lists_only(alice, bob, carol, make_list):
    own = make_list(alice, "Moja")
    shared = make_list(bob, "Od Boba", members=[alice])
    make_list(bob, "Cudza")
    make_list(carol, "Carol")

    response = alice.client.get("/api/lists/")
    assert response.status_code == 200
    by_name = {row["name"]: row for row in response.json()}
    assert set(by_name) == {own.name, shared.name}
    assert by_name["Moja"]["role"] == "owner"
    assert by_name["Od Boba"]["role"] == "member"


def test_list_counts_items(alice, make_list, make_item):
    lst = make_list(alice)
    make_item(lst, "a")
    make_item(lst, "b", is_purchased=True)
    row = alice.client.get("/api/lists/").json()[0]
    assert row["items_count"] == 2
    assert row["purchased_count"] == 1


def test_list_filter_archived(alice, make_list):
    make_list(alice, "aktywna")
    make_list(alice, "stara", is_archived=True)
    names = lambda qs: [r["name"] for r in alice.client.get(f"/api/lists/{qs}").json()]  # noqa: E731
    assert names("") and len(names("")) == 2
    assert names("?archived=true") == ["stara"]
    assert names("?archived=false") == ["aktywna"]


def test_list_filter_archived_rejects_garbage(alice):
    assert alice.client.get("/api/lists/?archived=maybe").status_code == 400


def test_retrieve_as_owner_and_member(alice, bob, make_list):
    lst = make_list(alice, members=[bob])
    assert alice.client.get(f"/api/lists/{lst.id}/").json()["role"] == "owner"
    assert bob.client.get(f"/api/lists/{lst.id}/").json()["role"] == "member"


def test_retrieve_without_access_is_forbidden(alice, carol, make_list):
    lst = make_list(alice)
    assert carol.client.get(f"/api/lists/{lst.id}/").status_code == 403


def test_retrieve_unknown_list_is_404(alice):
    assert alice.client.get(f"/api/lists/{uuid.uuid4()}/").status_code == 404


def test_retrieve_malformed_id_is_404(alice):
    assert alice.client.get("/api/lists/nie-uuid/").status_code == 404


# ---- edycja / usuwanie / archiwizacja


def test_owner_can_rename(alice, make_list):
    lst = make_list(alice)
    response = alice.client.patch(f"/api/lists/{lst.id}/", {"name": "Nowa nazwa"}, format="json")
    assert response.status_code == 200
    assert response.json()["name"] == "Nowa nazwa"


def test_patch_with_blank_name_is_rejected(alice, make_list):
    lst = make_list(alice)
    assert alice.client.patch(f"/api/lists/{lst.id}/", {"name": " "}, format="json").status_code == 400


def test_member_cannot_rename_or_delete(alice, bob, make_list):
    lst = make_list(alice, members=[bob])
    assert bob.client.patch(f"/api/lists/{lst.id}/", {"name": "x"}, format="json").status_code == 403
    assert bob.client.delete(f"/api/lists/{lst.id}/").status_code == 403


def test_stranger_cannot_modify(alice, carol, make_list):
    lst = make_list(alice)
    assert carol.client.patch(f"/api/lists/{lst.id}/", {"name": "x"}, format="json").status_code == 403
    assert carol.client.delete(f"/api/lists/{lst.id}/").status_code == 403


def test_owner_can_delete(alice, make_list):
    lst = make_list(alice)
    assert alice.client.delete(f"/api/lists/{lst.id}/").status_code == 204
    assert alice.client.get(f"/api/lists/{lst.id}/").status_code == 404


def test_archive_and_unarchive(alice, make_list):
    lst = make_list(alice)
    response = alice.client.post(f"/api/lists/{lst.id}/archive/")
    assert response.status_code == 200 and response.json()["is_archived"] is True
    # idempotentnie
    assert alice.client.post(f"/api/lists/{lst.id}/archive/").json()["is_archived"] is True
    response = alice.client.post(f"/api/lists/{lst.id}/unarchive/")
    assert response.json()["is_archived"] is False


def test_member_cannot_archive(alice, bob, make_list):
    lst = make_list(alice, members=[bob])
    assert bob.client.post(f"/api/lists/{lst.id}/archive/").status_code == 403
