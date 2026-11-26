from django.urls import path

from .consumers import ListConsumer, UserConsumer

websocket_urlpatterns = [
    path("ws/lists/<uuid:list_id>/", ListConsumer.as_asgi()),
    path("ws/me/", UserConsumer.as_asgi()),
]
