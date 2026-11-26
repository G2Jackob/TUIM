import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class ShoppingList(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="", max_length=1000)
    currency = models.CharField(max_length=3, default="PLN")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_lists"
    )
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.name


class ListMembership(models.Model):
    """Dostęp współtwórcy do listy. Właściciel nie ma wiersza – jest w `ShoppingList.owner`."""

    shopping_list = models.ForeignKey(
        ShoppingList, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="list_memberships"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["shopping_list", "user"], name="unique_list_member")
        ]


class ListInvite(models.Model):
    """Jednorazowy kod zaproszenia do listy."""

    shopping_list = models.ForeignKey(
        ShoppingList, on_delete=models.CASCADE, related_name="invites"
    )
    code = models.CharField(max_length=16, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    used_at = models.DateTimeField(null=True, blank=True)


class Item(models.Model):
    class Unit(models.TextChoices):
        PIECE = "szt", "szt."
        KILOGRAM = "kg", "kg"
        GRAM = "g", "g"
        LITER = "l", "l"
        MILLILITER = "ml", "ml"
        PACK = "opak", "opak."

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shopping_list = models.ForeignKey(
        ShoppingList, on_delete=models.CASCADE, related_name="items"
    )
    name = models.CharField(max_length=200)
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0.001"))],
    )
    unit = models.CharField(max_length=8, choices=Unit.choices, default=Unit.PIECE)
    category = models.CharField(max_length=50, blank=True, default="")
    # cena szacunkowa ZA JEDNĄ JEDNOSTKĘ (suma pozycji = quantity * estimated_price)
    estimated_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    note = models.CharField(max_length=500, blank=True, default="")

    reserved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reserved_items",
    )
    reserved_at = models.DateTimeField(null=True, blank=True)

    is_purchased = models.BooleanField(default=False)
    purchased_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="purchased_items",
    )
    purchased_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["is_purchased", "created_at"]

    def __str__(self) -> str:
        return self.name
