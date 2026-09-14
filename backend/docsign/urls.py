from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from docsign.views import root_view

app_urls = [
    path("admin/", admin.site.urls),
    path("auth/", include("auth_docsign.urls")),
    path("documentmanager/", include("documentmanager.urls")),
    path("signing/", include("integrations.urls")),
]

urlpatterns = [
    path("", root_view),
] + app_urls

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
