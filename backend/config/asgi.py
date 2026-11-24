"""ASGI: HTTP (Django/DRF) + WebSockety (Channels) z uwierzytelnianiem JWT.

Uruchamiane przez: daphne -b 0.0.0.0 -p 8000 config.asgi:application
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Najpierw inicjalizacja Django (rejestr aplikacji), dopiero potem importy routingu.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from accounts.ws_auth import JWTAuthMiddleware  # noqa: E402
from shopping.routing import websocket_urlpatterns  # noqa: E402

# Celowo bez AllowedHostsOriginValidator: klient to aplikacja natywna (brak nagłówka
# Origin), a uwierzytelnianie opiera się na tokenie JWT, nie na ciasteczkach.
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
