"""Rozsyłanie zdarzeń do klientów WebSocket przez Django Channels.

Wiadomość trafia do grupy kanałów:
  * `list_<uuid>`  – wszyscy podłączeni do danej listy,
  * `user_<id>`    – wszystkie urządzenia jednego użytkownika (np. „ktoś udostępnił Ci listę”).

Koperta zdarzenia (JSON):
  {"event": "item.created", "list_id": "...", "data": {...},
   "actor_id": 5, "timestamp": "2026-11-22T14:00:00+00:00"}

Wysyłka następuje po commicie transakcji. Awaria warstwy kanałów (np. Redis)
jest logowana i NIE psuje żądania HTTP – klient i tak dociągnie stan przez REST.
"""

import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# osobna zmienna, żeby testy mogły wykonywać callbacki od razu
_after_commit = transaction.on_commit


def list_group(list_id) -> str:
    return f"list_{list_id}"


def user_group(user_id) -> str:
    return f"user_{user_id}"


def _envelope(event: str, data, actor=None, **extra) -> dict:
    envelope = {
        "event": event,
        **extra,
        "data": data,
        "actor_id": getattr(actor, "id", None),
        "timestamp": timezone.now().isoformat(),
    }
    # normalizacja do czystego JSON-a (UUID, Decimal, daty) – wymagane przez Redis
    return json.loads(json.dumps(envelope, cls=DjangoJSONEncoder))


def _send(group: str, payload: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(group, {"type": "broadcast.event", "payload": payload})


def _publish(group: str, payload: dict) -> None:
    def _do():
        try:
            _send(group, payload)
        except Exception:  # noqa: BLE001 – warstwa kanałów nie może wywrócić requestu
            logger.exception("Nie udało się wysłać zdarzenia WebSocket do grupy %s", group)

    _after_commit(_do)


def publish_list_event(list_id, event: str, data, actor=None) -> None:
    _publish(list_group(list_id), _envelope(event, data, actor, list_id=str(list_id)))


def publish_user_event(user_id, event: str, data, actor=None) -> None:
    _publish(user_group(user_id), _envelope(event, data, actor))
