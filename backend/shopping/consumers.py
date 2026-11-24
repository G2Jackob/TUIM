"""Konsumenci WebSocket (Django Channels).

Kanał służy do ODBIERANIA zmian na żywo. Zmiany wysyłamy zwykłym REST API,
a serwer rozsyła je do wszystkich podłączonych klientów (patrz `events.py`).

Kody zamknięcia:  4401 – brak/zły token,  4403 – brak dostępu do listy,
                  4404 – lista została usunięta.
Wiadomości od klienta: {"action": "ping"} → {"event": "pong"}.
"""

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from . import services
from .events import list_group, user_group


class BaseEventConsumer(AsyncWebsocketConsumer):
    group: str | None = None

    async def send_json(self, content: dict) -> None:
        await self.send(text_data=json.dumps(content))

    async def authenticate(self):
        """Akceptuje połączenie i zwraca użytkownika; przy braku auth zamyka z kodem 4401."""
        await self.accept()
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.send_json(
                {"event": "error", "code": self.scope.get("auth_error") or "unauthenticated"}
            )
            await self.close(code=4401)
            return None
        return user

    async def join(self, group: str) -> None:
        self.group = group
        await self.channel_layer.group_add(group, self.channel_name)

    async def disconnect(self, code):
        if self.group:
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return
        try:
            message = json.loads(text_data)
        except ValueError:
            await self.send_json({"event": "error", "code": "invalid_json"})
            return
        if isinstance(message, dict) and message.get("action") == "ping":
            await self.send_json({"event": "pong"})
        else:
            await self.send_json(
                {
                    "event": "error",
                    "code": "unsupported_action",
                    "detail": "Zmiany wysyłaj przez REST API; WebSocket służy do odbierania zdarzeń.",
                }
            )

    async def broadcast_event(self, message):
        payload = message["payload"]
        await self.send_json(payload)
        await self.after_event(payload)

    async def after_event(self, payload: dict) -> None:
        pass


class ListConsumer(BaseEventConsumer):
    """ws/lists/<uuid>/ – zdarzenia jednej listy."""

    async def connect(self):
        self.list_id = self.scope["url_route"]["kwargs"]["list_id"]
        user = await self.authenticate()
        if user is None:
            return
        self.user = user

        allowed = await database_sync_to_async(services.has_list_access_by_id)(
            user.id, self.list_id
        )
        if not allowed:
            await self.send_json({"event": "error", "code": "forbidden"})
            await self.close(code=4403)
            return

        await self.join(list_group(self.list_id))
        await self.send_json({"event": "connection.ready", "list_id": str(self.list_id)})

    async def after_event(self, payload: dict) -> None:
        event = payload.get("event")
        if event == "member.removed" and payload["data"].get("user_id") == self.user.id:
            await self.close(code=4403)  # straciłem dostęp do listy
        elif event == "list.deleted":
            await self.close(code=4404)


class UserConsumer(BaseEventConsumer):
    """ws/me/ – zdarzenia dotyczące użytkownika (list.shared / list.unshared)."""

    async def connect(self):
        user = await self.authenticate()
        if user is None:
            return
        await self.join(user_group(user.id))
        await self.send_json({"event": "connection.ready", "user_id": user.id})
