from django.urls import include, path
from rest_framework import routers

from .views import DocumentSignDocumentViewSet, DocumentSignViewSet, DocumentViewSet

router = routers.DefaultRouter()
router.register(r"document", DocumentViewSet)
router.register(r"document-sign", DocumentSignViewSet)
router.register(r"sign-document", DocumentSignDocumentViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
