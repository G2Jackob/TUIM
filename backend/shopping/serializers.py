import re
from decimal import Decimal

from rest_framework import serializers

from accounts.serializers import UserBriefSerializer

from .models import Item, ListInvite, ShoppingList

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


def normalize_currency(value) -> str:
    value = (value or "").strip().upper()
    if not _CURRENCY_RE.match(value):
        raise serializers.ValidationError(
            "Waluta musi być trzyliterowym kodem ISO 4217, np. PLN lub EUR."
        )
    return value


class ShoppingListSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=120,
        error_messages={
            "blank": "Nazwa listy nie może być pusta.",
            "required": "Nazwa listy jest wymagana.",
        },
    )
    description = serializers.CharField(
        max_length=1000, required=False, allow_blank=True, default=""
    )
    currency = serializers.CharField(required=False, default="PLN")
    owner = UserBriefSerializer(read_only=True)
    role = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    purchased_count = serializers.SerializerMethodField()

    class Meta:
        model = ShoppingList
        fields = [
            "id",
            "name",
            "description",
            "currency",
            "is_archived",
            "owner",
            "role",
            "items_count",
            "purchased_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_archived", "created_at", "updated_at"]

    def validate_currency(self, value):
        return normalize_currency(value)

    def get_role(self, obj) -> str | None:
        request = self.context.get("request")
        if request is None:
            return None
        return "owner" if obj.owner_id == request.user.id else "member"

    def get_items_count(self, obj) -> int:
        value = getattr(obj, "items_count", None)
        return value if value is not None else obj.items.count()

    def get_purchased_count(self, obj) -> int:
        value = getattr(obj, "purchased_count", None)
        return value if value is not None else obj.items.filter(is_purchased=True).count()


class ListBroadcastSerializer(ShoppingListSerializer):
    """Wersja do rozsyłania przez WebSocket – bez pola `role` (zależy od odbiorcy)."""

    role = None

    class Meta(ShoppingListSerializer.Meta):
        fields = [f for f in ShoppingListSerializer.Meta.fields if f != "role"]


class ItemSerializer(serializers.ModelSerializer):
    list_id = serializers.UUIDField(source="shopping_list_id", read_only=True)
    name = serializers.CharField(
        max_length=200,
        error_messages={
            "blank": "Nazwa produktu nie może być pusta.",
            "required": "Nazwa produktu jest wymagana.",
        },
    )
    quantity = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        min_value=Decimal("0.001"),
        required=False,
        default=Decimal("1"),
        error_messages={
            "min_value": "Ilość musi być większa od zera.",
            "invalid": "Ilość musi być liczbą.",
        },
    )
    estimated_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
        error_messages={"min_value": "Cena nie może być ujemna."},
    )
    category = serializers.CharField(max_length=50, required=False, allow_blank=True)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
    reserved_by = UserBriefSerializer(read_only=True)
    purchased_by = UserBriefSerializer(read_only=True)

    class Meta:
        model = Item
        fields = [
            "id",
            "list_id",
            "name",
            "quantity",
            "unit",
            "category",
            "estimated_price",
            "note",
            "reserved_by",
            "reserved_at",
            "is_purchased",
            "purchased_by",
            "purchased_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reserved_at",
            "is_purchased",
            "purchased_at",
            "created_at",
            "updated_at",
        ]


class AddMemberSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        error_messages={
            "blank": "Podaj adres e-mail lub nazwę użytkownika.",
            "required": "Podaj adres e-mail lub nazwę użytkownika.",
        }
    )


class InviteSerializer(serializers.ModelSerializer):
    list_id = serializers.UUIDField(source="shopping_list_id", read_only=True)

    class Meta:
        model = ListInvite
        fields = ["code", "list_id", "expires_at"]
        read_only_fields = fields


class AcceptInviteSerializer(serializers.Serializer):
    code = serializers.CharField(
        error_messages={
            "blank": "Podaj kod zaproszenia.",
            "required": "Podaj kod zaproszenia.",
        }
    )
