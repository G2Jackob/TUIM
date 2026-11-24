from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import AcceptInviteView, ExchangeRateView, ItemViewSet, ShoppingListViewSet

router = SimpleRouter()
router.register("lists", ShoppingListViewSet, basename="list")

_items = "lists/<uuid:list_id>/items/"

urlpatterns = [
    *router.urls,
    path(_items, ItemViewSet.as_view({"get": "list", "post": "create"}), name="item-list"),
    path(
        f"{_items}<uuid:pk>/",
        ItemViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="item-detail",
    ),
    path(f"{_items}<uuid:pk>/reserve/", ItemViewSet.as_view({"post": "reserve"}), name="item-reserve"),
    path(f"{_items}<uuid:pk>/release/", ItemViewSet.as_view({"post": "release"}), name="item-release"),
    path(f"{_items}<uuid:pk>/purchase/", ItemViewSet.as_view({"post": "purchase"}), name="item-purchase"),
    path(
        f"{_items}<uuid:pk>/unpurchase/",
        ItemViewSet.as_view({"post": "unpurchase"}),
        name="item-unpurchase",
    ),
    path("invites/accept/", AcceptInviteView.as_view(), name="invite-accept"),
    path("exchange-rates/", ExchangeRateView.as_view(), name="exchange-rate"),
]
