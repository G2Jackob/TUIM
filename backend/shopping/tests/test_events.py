"""Czy każda zmiana stanu rozsyła właściwe zdarzenie do właściwej grupy WebSocket (FR-06)."""

import json

import pytest

from shopping import events

pytestmark = pytest.mark.django_db


def list_events(published, lst):
    group = f"list_{lst.id}"
    return [p for g, p in published if g == group]


def names(published, lst):
    return [p["event"] for p in list_events(published, lst)]


def user_events(published, user):
    return [p for g, p in published if g == f"user_{user.id}"]


# ---- produkty


def test_item_crud_events(alice, bob, make_list, published):
    lst = make_list(alice, members=[bob])
    created = alice.client.post(f"/api/lists/{lst.id}/items/", {"name": "Mleko"}, format="json").json()
    item_url = f"/api/lists/{lst.id}/items/{created['id']}/"
    alice.client.patch(item_url, {"name": "Mleko 2%"}, format="json")
    alice.client.delete(item_url)

    assert names(published, lst) == ["item.created", "item.updated", "item.deleted"]
    created_event, updated_event, deleted_event = list_events(published, lst)
    assert created_event["data"]["name"] == "Mleko"
    assert updated_event["data"]["name"] == "Mleko 2%"
    assert deleted_event["data"] == {"id": created["id"]}


def test_reservation_and_purchase_events(alice, bob, make_list, make_item, published):
    lst = make_list(alice, members=[bob])
    item = make_item(lst)
    base = f"/api/lists/{lst.id}/items/{item.id}"
    bob.client.post(f"{base}/reserve/")
    bob.client.post(f"{base}/release/")
    bob.client.post(f"{base}/purchase/")
    bob.client.post(f"{base}/unpurchase/")

    assert names(published, lst) == [
        "item.reserved",
        "item.released",
        "item.purchased",
        "item.unpurchased",
    ]
    reserved = list_events(published, lst)[0]
    assert reserved["data"]["reserved_by"]["username"] == "bob"
    assert reserved["actor_id"] == bob.user.id


def test_envelope_shape_and_json_serializable(alice, make_list, published):
    lst = make_list(alice)
    alice.client.post(
        f"/api/lists/{lst.id}/items/", {"name": "x", "estimated_price": "1.50"}, format="json"
    )
    group, payload = published[0]
    assert group == f"list_{lst.id}"
    assert set(payload) == {"event", "list_id", "data", "actor_id", "timestamp"}
    assert payload["list_id"] == str(lst.id)
    json.dumps(payload)  # czysty JSON – wymóg warstwy kanałów Redis


def test_no_event_when_request_fails(alice, bob, make_list, make_item, published):
    lst = make_list(alice, members=[bob])
    item = make_item(lst)
    alice.client.post(f"/api/lists/{lst.id}/items/", {"name": ""}, format="json")  # 400
    bob.client.post(f"/api/lists/{lst.id}/items/{item.id}/release/")  # 409
    assert published == []


def test_no_event_for_user_without_access(alice, carol, make_list, published):
    lst = make_list(alice)
    carol.client.post(f"/api/lists/{lst.id}/items/", {"name": "x"}, format="json")  # 403
    assert published == []


# ---- listy


def test_list_update_archive_and_delete_events(alice, bob, make_list, published):
    lst = make_list(alice, members=[bob])
    alice.client.patch(f"/api/lists/{lst.id}/", {"name": "Nowa"}, format="json")
    alice.client.post(f"/api/lists/{lst.id}/archive/")
    alice.client.post(f"/api/lists/{lst.id}/unarchive/")
    alice.client.delete(f"/api/lists/{lst.id}/")

    assert names(published, lst) == ["list.updated", "list.archived", "list.unarchived", "list.deleted"]
    updated = list_events(published, lst)[0]
    assert updated["data"]["name"] == "Nowa"
    assert "role" not in updated["data"]  # rola zależy od odbiorcy
    # członkowie dostają też zdarzenie na swoim kanale użytkownika
    assert [e["event"] for e in user_events(published, bob.user)] == ["list.unshared"]


def test_list_creation_publishes_nothing(alice, published):
    alice.client.post("/api/lists/", {"name": "x"}, format="json")
    assert published == []


# ---- członkowie


def test_member_added_events(alice, bob, make_list, published):
    lst = make_list(alice)
    alice.client.post(f"/api/lists/{lst.id}/members/", {"identifier": "bob"}, format="json")
    assert names(published, lst) == ["member.added"]
    assert list_events(published, lst)[0]["data"]["user"]["username"] == "bob"
    assert [e["event"] for e in user_events(published, bob.user)] == ["list.shared"]
    assert user_events(published, bob.user)[0]["data"]["id"] == str(lst.id)


def test_member_removed_events_include_released_items(alice, bob, make_list, make_item, published):
    from django.utils import timezone

    lst = make_list(alice, members=[bob])
    item = make_item(lst, reserved_by=bob.user, reserved_at=timezone.now())
    alice.client.delete(f"/api/lists/{lst.id}/members/{bob.user.id}/")

    removed = list_events(published, lst)[0]
    assert removed["event"] == "member.removed"
    assert removed["data"] == {"user_id": bob.user.id, "released_item_ids": [str(item.id)]}
    assert [e["event"] for e in user_events(published, bob.user)] == ["list.unshared"]


def test_accepting_invite_publishes_member_added(alice, bob, make_list, published):
    lst = make_list(alice)
    code = alice.client.post(f"/api/lists/{lst.id}/invites/").json()["code"]
    bob.client.post("/api/invites/accept/", {"code": code}, format="json")
    assert names(published, lst) == ["member.added"]


# ---- odporność


def test_channel_layer_failure_does_not_break_request(alice, make_list, monkeypatch):
    def boom(group, payload):
        raise ConnectionError("redis down")

    monkeypatch.setattr(events, "_send", boom)
    lst = make_list(alice)
    response = alice.client.post(f"/api/lists/{lst.id}/items/", {"name": "x"}, format="json")
    assert response.status_code == 201


def test_missing_channel_layer_is_ignored(monkeypatch):
    monkeypatch.setattr(events, "get_channel_layer", lambda: None)
    events._send("list_x", {"event": "x"})  # nie rzuca wyjątku
