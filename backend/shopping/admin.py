from django.contrib import admin

from .models import Item, ListInvite, ListMembership, ShoppingList


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "currency", "is_archived", "updated_at")
    search_fields = ("name", "owner__username")


admin.site.register(ListMembership)
admin.site.register(ListInvite)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "shopping_list", "quantity", "unit", "reserved_by", "is_purchased")
    list_filter = ("is_purchased",)
