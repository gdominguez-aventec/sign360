from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from documentmanager.utils.document_sign_config import is_document_sign_enabled


class DocumentSignConfigView(APIView):
    """
    Configuració que el frontal necessita conèixer del servidor.

    Es publica des d'aquí, i no com a variable d'entorn del frontal, perquè hi
    hagi una sola font de veritat: qui decideix si es poden posar més signants
    és el backend, que és qui ho valida.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "multi_signer_enabled": getattr(settings, "MULTI_SIGNER_ENABLED", False),
                "max_upload_size": getattr(
                    settings, "DOCUMENT_MAX_UPLOAD_SIZE", 20 * 1024 * 1024
                ),
                "signing_provider_configured": is_document_sign_enabled(),
            }
        )
