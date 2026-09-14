import json

import requests
from django.conf import settings

from integrations.models import IntegrationRequestLog

from .exceptions import SigningApiError

PROVIDER = "signing"
CREATE_SESSION_ENDPOINT = "/api/sessions/"
SESSION_DETAIL_ENDPOINT_TEMPLATE = "/api/sessions/{session_id}/"
SIGNED_DOCUMENT_ENDPOINT_TEMPLATE = (
    "/api/sessions/{session_id}/documents/{document_id}/signed/"
)


class SigningClient:
    """
    Client de l'API de signatura (Aqua360 Sign). Mateix contracte que el que fa
    servir `avsis-customers-backend`: es crea una sessió amb els documents i el
    proveïdor envia l'OTP al signant; el PDF firmat es descarrega a part quan
    arriba el callback.
    """

    def __init__(self, base_url=None, api_key=None, timeout=None):
        self.base_url = (base_url or settings.SIGNING_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.SIGNING_API_KEY
        self.timeout = timeout or getattr(settings, "SIGNING_TIMEOUT", 30)

    def _get_headers(self):
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _log_request(
        self,
        *,
        method,
        endpoint,
        request_payload,
        response_payload=None,
        status_code=None,
        success=False,
        error_message="",
        object_type="",
        object_id="",
    ):
        IntegrationRequestLog.objects.create(
            provider=PROVIDER,
            direction=IntegrationRequestLog.DIRECTION_OUTBOUND,
            method=method,
            endpoint=endpoint,
            request_payload=request_payload,
            response_payload=response_payload,
            status_code=status_code,
            success=success,
            error_message=error_message,
            object_type=object_type,
            object_id=object_id,
        )

    def _request(
        self,
        method,
        endpoint,
        *,
        log_payload,
        object_type="",
        object_id="",
        expect_json=True,
        **kwargs,
    ):
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method, url, headers=self._get_headers(), timeout=self.timeout, **kwargs
            )
        except requests.RequestException as exc:
            error_message = f"Error connectant amb el servei de signatura: {exc}"
            self._log_request(
                method=method,
                endpoint=endpoint,
                request_payload=log_payload,
                success=False,
                error_message=error_message,
                object_type=object_type,
                object_id=object_id,
            )
            raise SigningApiError(error_message) from exc

        if not response.ok:
            error_message = (
                f"Error resposta del servei de signatura {response.status_code}: {response.text}"
            )
            self._log_request(
                method=method,
                endpoint=endpoint,
                request_payload=log_payload,
                status_code=response.status_code,
                success=False,
                error_message=error_message,
                object_type=object_type,
                object_id=object_id,
            )
            raise SigningApiError(error_message)

        if not expect_json:
            self._log_request(
                method=method,
                endpoint=endpoint,
                request_payload=log_payload,
                status_code=response.status_code,
                success=True,
                object_type=object_type,
                object_id=object_id,
            )
            return response.content

        try:
            result = response.json()
        except ValueError as exc:
            error_message = "La resposta del servei de signatura no és JSON vàlid"
            self._log_request(
                method=method,
                endpoint=endpoint,
                request_payload=log_payload,
                status_code=response.status_code,
                success=False,
                error_message=error_message,
                object_type=object_type,
                object_id=object_id,
            )
            raise SigningApiError(error_message) from exc

        self._log_request(
            method=method,
            endpoint=endpoint,
            request_payload=log_payload,
            response_payload=result,
            status_code=response.status_code,
            success=True,
            object_type=object_type,
            object_id=object_id,
        )
        return result

    def create_session(
        self,
        *,
        recipient_name,
        recipient_email,
        documents,
        recipient_phone=None,
        external_reference=None,
        callback_url=None,
        document_metadata=None,
        object_type="",
        object_id="",
    ):
        """
        Crea una sessió de signatura.

        `documents`: llista de tuples (filename, bytes, content_type).
        """
        data = {
            "recipient_name": recipient_name,
            "recipient_email": recipient_email,
        }
        if recipient_phone:
            data["recipient_phone"] = recipient_phone
        if external_reference:
            data["external_reference"] = external_reference
        if callback_url:
            data["callback_url"] = callback_url
        if document_metadata is not None:
            data["document_metadata"] = json.dumps(document_metadata)

        files = [
            ("documents", (filename, content, content_type or "application/pdf"))
            for filename, content, content_type in documents
        ]

        log_payload = {**data, "documents": [filename for filename, _, _ in documents]}

        return self._request(
            "POST",
            CREATE_SESSION_ENDPOINT,
            data=data,
            files=files,
            log_payload=log_payload,
            object_type=object_type,
            object_id=object_id,
        )

    def get_session(self, session_id, *, object_type="", object_id=""):
        endpoint = SESSION_DETAIL_ENDPOINT_TEMPLATE.format(session_id=session_id)
        return self._request(
            "GET",
            endpoint,
            log_payload={"session_id": session_id},
            object_type=object_type,
            object_id=object_id,
        )

    def download_signed_document(self, session_id, document_id, *, object_type="", object_id=""):
        """
        Descarrega el PDF firmat d'un document de la sessió:
        GET /api/sessions/<session_id>/documents/<document_id>/signed/
        """
        endpoint = SIGNED_DOCUMENT_ENDPOINT_TEMPLATE.format(
            session_id=session_id, document_id=document_id
        )
        return self._request(
            "GET",
            endpoint,
            log_payload={"session_id": session_id, "document_id": document_id},
            expect_json=False,
            object_type=object_type,
            object_id=object_id,
        )
