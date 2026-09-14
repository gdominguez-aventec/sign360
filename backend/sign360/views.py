from django.conf import settings
from django.http import JsonResponse


def root_view(request):
    return JsonResponse(
        {
            "name": "sign360",
            "description": "API de gestió i signatura de documents",
            "env": settings.ENV,
        }
    )
