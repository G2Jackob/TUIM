"""Testy integracyjne WebSocketów: uwierzytelnianie JWT, autoryzacja listy, rozsyłanie zmian.

Używają prawdziwej (in-memory) warstwy kanałów i bazy danych (transaction=True),
a zmiany wyzwalane są prawdziwymi żądaniami HTTP.
"""


import pytest
from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from jwt.exceptions import PyJWKClientConnectionError

from accounts import tokens
from accounts.ws_auth import JWTAuthMiddleware, extract_token
from shopping.routing import websocket_urlpatterns

application = JWTAuthMiddleware(URLRouter(websocket_urlpatterns))
pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
async def ws():
    opened = []

    async def _connect(path, token=None, via_query=False, headers=None):
        headers = list(headers or [])
        if token and via_query:
            path += f"?token={token}"
        elif token:
            headers.append((b"authorization", f"Bearer {token}".encode()))
        communicator = WebsocketCommunicator(application, path, headers=headers)
        opened.append(communicator)
        connected, _ = await communicator.connect()
        assert connected
        return communicator

    yield _connect
    for communicator in opened:
        try:
            await communicator.disconnect()
        except Exception:  # noqa: BLE001
            pass


async def collect_until_close(communicator):
    """Zbiera wiadomości tekstowe aż do ramki zamknięcia; zwraca (wiadomości, kod)."""
    messages = []
    while True:
        output = await communicator.receive_output(timeout=2)
        if output["type"] == "websocket.close":
            return messages, output["code"]
        messages.append(output["text"])


async def http(client, method, path, data=None):
    func = getattr(client, method)
    kwargs = {"format": "json"} if data is not None else {}
    return await sync_to_async(func)(path, *([data] if data is not None else []), **kwargs)


# ---------------------------------------------------------------- uwierzytelnianie


async def test_connect_with_bearer_header(ws, alice, make_list):
    lst = await sync_to_async(make_list)(alice)
    communicator = await ws(f"/ws/lists/{lst.id}/", token=alice.token)
    assert await communicator.receive_json_from(timeout=2) == {
        "event": "connection.ready",
        "list_id": str(lst.id),
    }


async def test_connect_with_query_token(ws, alice, make_list):
    lst = await sync_to_async(make_list)(alice)
    communicator = await ws(f"/ws/lists/{lst.id}/", token=alice.token, via_query=True)
    assert (await communicator.receive_json_from(timeout=2))["event"] == "connection.ready"


async def test_missing_token_is_rejected_with_4401(ws, alice, make_list):
    lst = await sync_to_async(make_list)(alice)
    communicator = await ws(f"/ws/lists/{lst.id}/")
    messages, code = await collect_until_close(communicator)
    assert code == 4401
    assert '"missing_token"' in messages[0]


async def test_expired_token_is_rejected_with_reason(ws, alice, make_list, make_token):
    lst = await sync_to_async(make_list)(alice)
    expired = make_token(sub=alice.sub, expires_in=-30)
    communicator = await ws(f"/ws/lists/{lst.id}/", token=expired)
    messages, code = await collect_until_close(communicator)
    assert code == 4401 and '"token_expired"' in messages[0]


async def test_garbage_token_is_rejected(ws, alice, make_list):
    lst = await sync_to_async(make_list)(alice)
    communicator = await ws(f"/ws/lists/{lst.id}/", token="bzdura")
    messages, code = await collect_until_close(communicator)
    assert code == 4401 and '"invalid_token"' in messages[0]


async def test_keycloak_down_is_reported(ws, alice, make_list, monkeypatch):
    lst = await sync_to_async(make_list)(alice)

    def boom(token):
        raise PyJWKClientConnectionError("down")

    monkeypatch.setattr(tokens, "get_signing_key", boom)
    communicator = await ws(f"/ws/lists/{lst.id}/", token=alice.token)
    messages, code = await collect_until_close(communicator)
    assert code == 4401 and '"auth_service_unavailable"' in messages[0]


async def test_malformed_authorization_header_is_ignored(ws, alice, make_list):
    lst = await sync_to_async(make_list)(alice)
    communicator = await ws(
        f"/ws/lists/{lst.id}/", headers=[(b"authorization", b"Basic dXNlcjpwYXNz")]
    )
    _, code = await collect_until_close(communicator)
    assert code == 4401


def test_extract_token_prefers_header_over_query():
    scope = {
        "headers": [(b"authorization", b"Bearer from-header")],
        "query_string": b"token=from-query",
    }
    assert extract_token(scope) == "from-header"
    assert extract_token({"headers": [], "query_string": b"token=q"}) == "q"
    assert extract_token({"headers": [], "query_string": b""}) is None
    assert extract_token({}) is None


async def test_middleware_passes_through_non_websocket_scopes():
    seen = {}

    async def inner(scope, receive, send):
        seen["scope"] = scope

    scope = {"type": "http"}
    await JWTAuthMiddleware(inner)(scope, None, None)
    assert seen["scope"] is scope


# ---------------------------------------------------------------- autoryzacja listy


async def test_user_without_access_gets_4403(ws, alice, carol, make_list):
    lst = await sync_to_async(make_list)(alice)
    communicator = await ws(f"/ws/lists/{lst.id}/", token=carol.token)
    messages, code = await collect_until_close(communicator)
    assert code == 4403 and '"forbidden"' in messages[0]


async def test_unknown_list_gets_4403(ws, alice):
    import uuid

    communicator = await ws(f"/ws/lists/{uuid.uuid4()}/", token=alice.token)
    _, code = await collect_until_close(communicator)
    assert code == 4403


async def test_member_can_connect(ws, alice, bob, make_list):
    lst = await sync_to_async(make_list)(alice, members=[bob])
    communicator = await ws(f"/ws/lists/{lst.id}/", token=bob.token)
    assert (await communicator.receive_json_from(timeout=2))["event"] == "connection.ready"


# ---------------------------------------------------------------- zmiany na żywo


async def test_other_member_sees_new_item_without_refresh(ws, alice, bob, make_list):
    lst = await sync_to_async(make_list)(alice, members=[bob])
    bob_socket = await ws(f"/ws/lists/{lst.id}/", token=bob.token)
    await bob_socket.receive_json_from(timeout=2)  # connection.ready

    response = await http(alice.client, "post", f"/api/lists/{lst.id}/items/", {"name": "Chleb"})
    assert response.status_code == 201

    event = await bob_socket.receive_json_from(timeout=2)
    assert event["event"] == "item.created"
    assert event["data"]["name"] == "Chleb"
    assert event["actor_id"] == alice.user.id


async def test_reservation_is_broadcast_to_all_clients_of_the_list(ws, alice, bob, make_list, make_item):
    lst = await sync_to_async(make_list)(alice, members=[bob])
    item = await sync_to_async(make_item)(lst)
    sockets = [await ws(f"/ws/lists/{lst.id}/", token=a.token) for a in (alice, bob)]
    for socket in sockets:
        await socket.receive_json_from(timeout=2)

    await http(bob.client, "post", f"/api/lists/{lst.id}/items/{item.id}/reserve/")

    for socket in sockets:
        event = await socket.receive_json_from(timeout=2)
        assert event["event"] == "item.reserved"
        assert event["data"]["reserved_by"]["username"] == "bob"


async def test_events_do_not_leak_to_other_lists(ws, alice, make_list):
    lst1 = await sync_to_async(make_list)(alice, "A")
    lst2 = await sync_to_async(make_list)(alice, "B")
    socket2 = await ws(f"/ws/lists/{lst2.id}/", token=alice.token)
    await socket2.receive_json_from(timeout=2)

    await http(alice.client, "post", f"/api/lists/{lst1.id}/items/", {"name": "x"})
    assert await socket2.receive_nothing(timeout=0.3)


async def test_removed_member_is_notified_and_disconnected(ws, alice, bob, carol, make_list):
    lst = await sync_to_async(make_list)(alice, members=[bob, carol])
    bob_socket = await ws(f"/ws/lists/{lst.id}/", token=bob.token)
    carol_socket = await ws(f"/ws/lists/{lst.id}/", token=carol.token)
    await bob_socket.receive_json_from(timeout=2)
    await carol_socket.receive_json_from(timeout=2)

    await http(alice.client, "delete", f"/api/lists/{lst.id}/members/{bob.user.id}/")

    messages, code = await collect_until_close(bob_socket)
    assert code == 4403 and '"member.removed"' in messages[0]
    # reszta członków dostaje zdarzenie, ale zostaje podłączona
    assert (await carol_socket.receive_json_from(timeout=2))["event"] == "member.removed"
    assert await carol_socket.receive_nothing(timeout=0.3)

    # utracony dostęp działa też dla nowych połączeń
    again = await ws(f"/ws/lists/{lst.id}/", token=bob.token)
    _, code = await collect_until_close(again)
    assert code == 4403


async def test_deleting_list_closes_connections_with_4404(ws, alice, bob, make_list):
    lst = await sync_to_async(make_list)(alice, members=[bob])
    socket = await ws(f"/ws/lists/{lst.id}/", token=bob.token)
    await socket.receive_json_from(timeout=2)

    await http(alice.client, "delete", f"/api/lists/{lst.id}/")

    messages, code = await collect_until_close(socket)
    assert code == 4404 and '"list.deleted"' in messages[0]


# ---------------------------------------------------------------- wiadomości od klienta


async def test_ping_pong(ws, alice, make_list):
    lst = await sync_to_async(make_list)(alice)
    socket = await ws(f"/ws/lists/{lst.id}/", token=alice.token)
    await socket.receive_json_from(timeout=2)
    await socket.send_json_to({"action": "ping"})
    assert await socket.receive_json_from(timeout=2) == {"event": "pong"}


async def test_invalid_json_gets_error_event(ws, alice, make_list):
    lst = await sync_to_async(make_list)(alice)
    socket = await ws(f"/ws/lists/{lst.id}/", token=alice.token)
    await socket.receive_json_from(timeout=2)
    await socket.send_to(text_data="{nie json")
    assert (await socket.receive_json_from(timeout=2))["code"] == "invalid_json"


async def test_writes_over_websocket_are_not_supported(ws, alice, make_list):
    lst = await sync_to_async(make_list)(alice)
    socket = await ws(f"/ws/lists/{lst.id}/", token=alice.token)
    await socket.receive_json_from(timeout=2)
    await socket.send_json_to({"action": "add_item", "name": "x"})
    assert (await socket.receive_json_from(timeout=2))["code"] == "unsupported_action"
    items = await sync_to_async(lambda: lst.items.count())()
    assert items == 0


async def test_binary_frames_are_ignored(ws, alice, make_list):
    lst = await sync_to_async(make_list)(alice)
    socket = await ws(f"/ws/lists/{lst.id}/", token=alice.token)
    await socket.receive_json_from(timeout=2)
    await socket.send_to(bytes_data=b"\x00\x01")
    assert await socket.receive_nothing(timeout=0.3)


# ---------------------------------------------------------------- kanał użytkownika /ws/me/


async def test_user_channel_receives_list_shared_event(ws, alice, bob, make_list):
    lst = await sync_to_async(make_list)(alice)
    bob_socket = await ws("/ws/me/", token=bob.token)
    assert (await bob_socket.receive_json_from(timeout=2))["event"] == "connection.ready"

    await http(alice.client, "post", f"/api/lists/{lst.id}/members/", {"identifier": "bob"})

    event = await bob_socket.receive_json_from(timeout=2)
    assert event["event"] == "list.shared"
    assert event["data"]["name"] == "Zakupy"


async def test_user_channel_requires_auth(ws):
    socket = await ws("/ws/me/")
    _, code = await collect_until_close(socket)
    assert code == 4401


async def test_user_channel_does_not_receive_other_users_events(ws, alice, bob, carol, make_list):
    lst = await sync_to_async(make_list)(alice)
    carol_socket = await ws("/ws/me/", token=carol.token)
    await carol_socket.receive_json_from(timeout=2)
    await http(alice.client, "post", f"/api/lists/{lst.id}/members/", {"identifier": "bob"})
    assert await carol_socket.receive_nothing(timeout=0.3)
