from django.urls import include, path
from rest_framework import routers

from .views import DocumentSignViewSet, DocumentViewSet

router = routers.DefaultRouter()
router.register(r"document", DocumentViewSet)
router.register(r"document-sign", DocumentSignViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
