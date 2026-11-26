from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "display_name"]
        read_only_fields = fields

    def get_display_name(self, obj) -> str:
        return obj.get_full_name().strip() or obj.username


class MeSerializer(UserBriefSerializer):
    keycloak_id = serializers.CharField(source="profile.keycloak_id", read_only=True)

    class Meta(UserBriefSerializer.Meta):
        fields = ["id", "username", "email", "display_name", "keycloak_id"]
        read_only_fields = fields
