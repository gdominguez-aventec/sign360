from django.urls import include, path
from rest_framework import routers

from .views import (
    CustomAuthToken,
    GroupViewSet,
    LogoutView,
    MeView,
    UserPermissionsView,
    UserViewSet,
)

router = routers.DefaultRouter()
router.register(r"user", UserViewSet)
router.register(r"group", GroupViewSet)

urlpatterns = [
    path("login/", CustomAuthToken.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    # Ha d'anar abans d'`include(router.urls)`: el router registra `<recurs>/<pk>/`
    # amb un patró de pk genèric que capturaria aquestes rutes com a pk.
    path("permission/my-permissions/", UserPermissionsView.as_view(), name="my-permissions"),
    path("", include(router.urls)),
]
