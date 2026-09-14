from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from integrations.inbound.signing.services import (
    SUPPORTED_EVENTS,
    SigningCallbackError,
    handle_signing_callback,
    log_signing_callback,
)


class SigningCallbackView(APIView):
    """Webhook del proveïdor de signatura. No passa per l'autenticació de DRF."""

    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        payload = request.data

        # Només es valida si s'ha configurat una clau al nostre costat; en local
        # es pot deixar buida per poder provar el webhook sense credencials.
        expected_key = getattr(settings, "SIGN_CALLBACK_API_KEY", "")
        received_key = request.headers.get("X-API-Key", "")
        if expected_key and received_key != expected_key:
            return self._fail(payload, "No autoritzat.", status.HTTP_403_FORBIDDEN)

        if payload.get("event") not in SUPPORTED_EVENTS:
            return self._fail(payload, "Esdeveniment no suportat.", status.HTTP_400_BAD_REQUEST)

        if not (payload.get("external_reference") or "").strip():
            return self._fail(
                payload, "external_reference és obligatori.", status.HTTP_400_BAD_REQUEST
            )

        try:
            result = handle_signing_callback(payload)
        except SigningCallbackError as exc:
            return self._fail(payload, exc.detail, exc.status_code)
        except Exception as exc:
            return self._fail(payload, str(exc), status.HTTP_400_BAD_REQUEST)

        log_signing_callback(
            payload, success=True, status_code=status.HTTP_200_OK, response_payload=result
        )
        return Response(result, status=status.HTTP_200_OK)

    def _fail(self, payload, detail, status_code):
        log_signing_callback(
            payload,
            success=False,
            status_code=status_code,
            error_message=str(detail),
            response_payload={"detail": detail},
        )
        return Response({"detail": detail}, status=status_code)
