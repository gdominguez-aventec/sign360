from django.urls import include, path
from rest_framework import routers

from .config_views import DocumentSignConfigView
from .views import DocumentSignDocumentViewSet, DocumentSignViewSet, DocumentViewSet

router = routers.DefaultRouter()
router.register(r"document", DocumentViewSet)
router.register(r"document-sign", DocumentSignViewSet)
router.register(r"sign-document", DocumentSignDocumentViewSet)

urlpatterns = [
    # Ha d'anar abans d'`include(router.urls)`: el router registra rutes amb un
    # patró de pk genèric que podria capturar "config" com a pk.
    path("config/", DocumentSignConfigView.as_view(), name="document-sign-config"),
    path("", include(router.urls)),
]
