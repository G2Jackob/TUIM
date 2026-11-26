from django.urls import path

from .views import AuthConfigView, MeView

urlpatterns = [
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("auth/config/", AuthConfigView.as_view(), name="auth-config"),
]
