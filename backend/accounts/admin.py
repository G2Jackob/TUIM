from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "keycloak_id", "created_at")
    search_fields = ("user__username", "user__email", "keycloak_id")
