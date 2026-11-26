from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import UserBriefSerializer

from . import events, fx, services
from .models import Item, ShoppingList
from .serializers import (
    AcceptInviteSerializer,
    AddMemberSerializer,
    InviteSerializer,
    ItemSerializer,
    ListBroadcastSerializer,
    ShoppingListSerializer,
    normalize_currency,
)


def _currency_param(value, name: str = "currency") -> str:
    try:
        return normalize_currency(value)
    except serializers.ValidationError as exc:
        raise serializers.ValidationError({name: exc.detail}) from exc


def _member_data(user, joined_at, role: str) -> dict:
    return {"user": UserBriefSerializer(user).data, "role": role, "joined_at": joined_at}


# ------------------------------------------------------------------ listy


class ListAccessPermission(BasePermission):
    message = "Nie masz uprawnień do wykonania tej operacji na tej liście."

    def has_object_permission(self, request, view, obj):
        if view.requires_owner():
            return services.is_owner(request.user, obj)
        return services.has_access(request.user, obj)


class ShoppingListViewSet(viewsets.ModelViewSet):
    """CRUD list zakupów + członkowie, zaproszenia i suma.

    Właściciel: zmiana/usuwanie/archiwizacja, udostępnianie, zaproszenia.
    Członek: podgląd listy, członków i sumy (+ opuszczenie listy).
    """

    serializer_class = ShoppingListSerializer
    permission_classes = [IsAuthenticated, ListAccessPermission]
    lookup_value_regex = "[0-9a-fA-F-]{36}"

    OWNER_ACTIONS = {"update", "partial_update", "destroy", "archive", "unarchive", "invites"}

    def requires_owner(self) -> bool:
        if self.action in self.OWNER_ACTIONS:
            return True
        return self.action == "members" and self.request.method == "POST"

    def get_queryset(self):
        queryset = services.lists_with_counts()
        if self.action != "list":
            return queryset
        queryset = queryset.filter(services.access_filter(self.request.user.id))
        archived = self.request.query_params.get("archived")
        if archived is not None:
            if archived.lower() not in ("true", "false"):
                raise serializers.ValidationError(
                    {"archived": ["Dozwolone wartości: true lub false."]}
                )
            queryset = queryset.filter(is_archived=archived.lower() == "true")
        return queryset

    # -- CRUD

    @extend_schema(
        parameters=[OpenApiParameter("archived", bool, description="Filtr: tylko (nie)zarchiwizowane")]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        lst = serializer.save()
        events.publish_list_event(
            lst.id, "list.updated", ListBroadcastSerializer(lst).data, self.request.user
        )

    def perform_destroy(self, instance):
        list_id = instance.id
        member_ids = list(instance.memberships.values_list("user_id", flat=True))
        instance.delete()
        actor = self.request.user
        events.publish_list_event(list_id, "list.deleted", {"id": str(list_id)}, actor)
        for user_id in member_ids:
            events.publish_user_event(user_id, "list.unshared", {"list_id": str(list_id)}, actor)

    # -- archiwizacja

    @extend_schema(request=None, responses=ShoppingListSerializer)
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        return self._set_archived(True, "list.archived")

    @extend_schema(request=None, responses=ShoppingListSerializer)
    @action(detail=True, methods=["post"])
    def unarchive(self, request, pk=None):
        return self._set_archived(False, "list.unarchived")

    def _set_archived(self, value: bool, event: str):
        lst = services.set_archived(self.get_object(), value)
        events.publish_list_event(
            lst.id, event, ListBroadcastSerializer(lst).data, self.request.user
        )
        return Response(self.get_serializer(lst).data)

    # -- członkowie

    @extend_schema(
        methods=["POST"], request=AddMemberSerializer, responses={201: dict}
    )
    @extend_schema(methods=["GET"], responses={200: dict(type="array")})
    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        lst = self.get_object()

        if request.method == "POST":
            serializer = AddMemberSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            target, membership = services.add_member(lst, serializer.validated_data["identifier"])
            data = _member_data(target, membership.created_at, "member")
            events.publish_list_event(lst.id, "member.added", data, request.user)
            events.publish_user_event(
                target.id, "list.shared", ListBroadcastSerializer(lst).data, request.user
            )
            return Response(data, status=status.HTTP_201_CREATED)

        memberships = lst.memberships.select_related("user").order_by("created_at")
        data = [_member_data(lst.owner, lst.created_at, "owner")]
        data += [_member_data(m.user, m.created_at, "member") for m in memberships]
        return Response(data)

    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=["delete"], url_path=r"members/(?P<user_id>[0-9]+)")
    def remove_member(self, request, pk=None, user_id=None):
        lst = self.get_object()
        user_id = int(user_id)
        released_ids = services.remove_member(lst, request.user, user_id)
        events.publish_list_event(
            lst.id,
            "member.removed",
            {"user_id": user_id, "released_item_ids": [str(i) for i in released_ids]},
            request.user,
        )
        events.publish_user_event(
            user_id, "list.unshared", {"list_id": str(lst.id)}, request.user
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # -- zaproszenia

    @extend_schema(request=None, responses={201: InviteSerializer})
    @action(detail=True, methods=["post"])
    def invites(self, request, pk=None):
        invite = services.create_invite(self.get_object(), request.user)
        return Response(InviteSerializer(invite).data, status=status.HTTP_201_CREATED)

    # -- suma + przeliczenie waluty (zewnętrzne API)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "currency", str, description="Waluta docelowa (ISO 4217), np. EUR. Bez niej – bez przeliczenia."
            )
        ],
        responses=dict,
    )
    @action(detail=True, methods=["get"])
    def total(self, request, pk=None):
        lst = self.get_object()
        target = request.query_params.get("currency")
        if target is not None:
            target = _currency_param(target)
        return Response(services.list_total(lst, target))


class AcceptInviteView(APIView):
    @extend_schema(request=AcceptInviteSerializer, responses=ShoppingListSerializer)
    def post(self, request):
        serializer = AcceptInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lst = services.accept_invite(serializer.validated_data["code"], request.user)

        membership = lst.memberships.select_related("user").get(user=request.user)
        events.publish_list_event(
            lst.id,
            "member.added",
            _member_data(request.user, membership.created_at, "member"),
            request.user,
        )
        lst = services.lists_with_counts().get(pk=lst.pk)
        return Response(ShoppingListSerializer(lst, context={"request": request}).data)


class ExchangeRateView(APIView):
    """Kurs wymiany walut z zewnętrznego API (NBP)."""

    @extend_schema(
        parameters=[
            OpenApiParameter("from", str, description="Waluta źródłowa, domyślnie PLN"),
            OpenApiParameter("to", str, required=True, description="Waluta docelowa"),
        ],
        responses=dict,
    )
    def get(self, request):
        to_code = request.query_params.get("to")
        if not to_code:
            raise serializers.ValidationError({"to": ["Parametr 'to' jest wymagany."]})
        from_code = _currency_param(request.query_params.get("from", "PLN"), "from")
        to_code = _currency_param(to_code, "to")
        rate = fx.get_rate(from_code, to_code)
        return Response(
            {
                "from": from_code,
                "to": to_code,
                "rate": str(rate.rate),
                "rate_date": rate.date,
                "stale": rate.stale,
            }
        )


# ------------------------------------------------------------------ produkty


class ItemViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Produkty na liście: /api/lists/<list_id>/items/..."""

    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated]

    def get_shopping_list(self) -> ShoppingList:
        if not hasattr(self, "_shopping_list"):
            lst = get_object_or_404(ShoppingList, pk=self.kwargs["list_id"])
            if not services.has_access(self.request.user, lst):
                raise PermissionDenied("Nie masz dostępu do tej listy.")
            self._shopping_list = lst
        return self._shopping_list

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        lst = self.get_shopping_list()  # 404 / 403
        if request.method not in SAFE_METHODS:
            services.ensure_writable(lst)  # 409 dla zarchiwizowanej listy

    def get_queryset(self):
        return Item.objects.filter(shopping_list=self.get_shopping_list()).select_related(
            "reserved_by", "purchased_by"
        )

    def _emit(self, event: str, item: Item) -> None:
        events.publish_list_event(
            item.shopping_list_id, event, ItemSerializer(item).data, self.request.user
        )

    def perform_create(self, serializer):
        item = serializer.save(shopping_list=self.get_shopping_list())
        self._emit("item.created", item)

    def perform_update(self, serializer):
        self._emit("item.updated", serializer.save())

    def perform_destroy(self, instance):
        list_id, item_id = instance.shopping_list_id, str(instance.id)
        instance.delete()
        events.publish_list_event(list_id, "item.deleted", {"id": item_id}, self.request.user)

    # -- rezerwacja i zakup

    def _transition(self, request, service, event: str):
        item = service(self.get_object().pk, request.user)
        self._emit(event, item)
        return Response(ItemSerializer(item).data)

    @extend_schema(request=None, responses=ItemSerializer)
    @action(detail=True, methods=["post"])
    def reserve(self, request, **kwargs):
        return self._transition(request, services.reserve_item, "item.reserved")

    @extend_schema(request=None, responses=ItemSerializer)
    @action(detail=True, methods=["post"])
    def release(self, request, **kwargs):
        return self._transition(request, services.release_item, "item.released")

    @extend_schema(request=None, responses=ItemSerializer)
    @action(detail=True, methods=["post"])
    def purchase(self, request, **kwargs):
        return self._transition(request, services.purchase_item, "item.purchased")

    @extend_schema(request=None, responses=ItemSerializer)
    @action(detail=True, methods=["post"])
    def unpurchase(self, request, **kwargs):
        return self._transition(request, services.unpurchase_item, "item.unpurchased")
