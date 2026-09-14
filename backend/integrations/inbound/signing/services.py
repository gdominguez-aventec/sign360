from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from documentmanager.models import DocumentSign
from documentmanager.utils.document_sign_config import DOCUMENT_SIGN_REFERENCE_PREFIX
from documentmanager.utils.main_utils import get_default_service, upload_document
from integrations.models import IntegrationRequestLog, SigningSession
from integrations.outbound.signing.client import SigningClient
from integrations.outbound.signing.exceptions import SigningApiError

PROVIDER = "signing"
CALLBACK_ENDPOINT = "/signing/callback/"

SUPPORTED_EVENTS = ("session.signed", "session.expired")


class SigningCallbackError(Exception):
    def __init__(self, detail, status_code=400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _parse_signed_at(value):
    if not value:
        return timezone.now()
    return parse_datetime(value) or timezone.now()


def _resolve_document_sign(external_reference):
    ref = (external_reference or "").strip()
    if not ref:
        return None
    if ref.startswith(DOCUMENT_SIGN_REFERENCE_PREFIX):
        ref = ref[len(DOCUMENT_SIGN_REFERENCE_PREFIX):]
    document_sign = DocumentSign.objects.filter(token=ref).first()
    if document_sign:
        return document_sign
    if ref.isdigit():
        return DocumentSign.objects.filter(id=int(ref)).first()
    return None


def save_signed_document_file(document_sign, pdf_bytes, signed_at):
    filename = f"{document_sign.token}_signed.pdf"
    file_obj = SimpleUploadedFile(filename, pdf_bytes, content_type="application/pdf")
    document = upload_document(
        file_obj,
        "DOCUMENT_SIGN",
        entity_id=document_sign.id,
        entity_token=document_sign.token,
        folder="signed",
        document_name=filename,
        service=get_default_service(),
        content_type="application/pdf",
    )

    document_sign.document_file_signed = document
    document_sign.status = DocumentSign.STATUS_SIGNED
    document_sign.signed_at = signed_at
    document_sign.error_report = None
    document_sign.save(
        update_fields=[
            "document_file_signed",
            "status",
            "signed_at",
            "error_report",
            "updated_at",
        ]
    )
    return document


def _download_signed_pdf(session_id, payload):
    """
    El webhook `session.signed` només notifica l'esdeveniment; el PDF firmat
    s'ha de descarregar a part del proveïdor.
    """
    if not session_id:
        return None

    documents = payload.get("documents") or []
    signed_document = next(
        (
            document
            for document in documents
            if isinstance(document, dict) and document.get("signed") and document.get("id")
        ),
        None,
    )
    if not signed_document:
        return None

    try:
        return SigningClient().download_signed_document(session_id, signed_document["id"])
    except SigningApiError:
        return None


def handle_signing_callback(payload):
    event = payload.get("event")
    external_reference = (payload.get("external_reference") or "").strip()
    session_id = (payload.get("session_id") or "").strip()

    if session_id:
        existing = SigningSession.objects.filter(session_id=session_id).first()
        if existing and existing.status == SigningSession.STATUS_SIGNED:
            # El proveïdor reintenta els webhooks; una sessió ja processada no
            # s'ha de tornar a descarregar ni a sobreescriure.
            return {"ok": True, "already_processed": True}

    document_sign = _resolve_document_sign(external_reference)
    if not document_sign:
        raise SigningCallbackError(
            "No s'ha trobat cap document per firmar amb aquesta referència.",
            status_code=404,
        )

    if event == "session.expired":
        return _handle_expired(document_sign, session_id)
    return _handle_signed(document_sign, session_id, payload)


def _handle_signed(document_sign, session_id, payload):
    signed_at = _parse_signed_at(payload.get("signed_at"))
    pdf_bytes = _download_signed_pdf(session_id, payload)

    if not pdf_bytes:
        raise SigningCallbackError(
            "No s'ha pogut descarregar el document firmat del servei de signatura.",
            status_code=400,
        )

    save_signed_document_file(document_sign, pdf_bytes, signed_at)

    session = SigningSession.objects.filter(session_id=session_id).first() if session_id else None
    if session:
        session.status = SigningSession.STATUS_SIGNED
        session.signed_at = signed_at
        session.save(update_fields=["status", "signed_at", "updated_at"])

    return {
        "ok": True,
        "document_sign_id": document_sign.id,
        "document_sign_token": document_sign.token,
        "session_id": session_id or None,
        "document_file_saved": True,
    }


def _handle_expired(document_sign, session_id):
    session = SigningSession.objects.filter(session_id=session_id).first() if session_id else None
    if session and session.status != SigningSession.STATUS_SIGNED:
        session.status = SigningSession.STATUS_EXPIRED
        session.save(update_fields=["status", "updated_at"])

    if document_sign.status != DocumentSign.STATUS_SIGNED:
        document_sign.status = DocumentSign.STATUS_EXPIRED
        document_sign.error_report = None
        document_sign.save(update_fields=["status", "error_report", "updated_at"])

    return {
        "ok": True,
        "document_sign_id": document_sign.id,
        "document_sign_token": document_sign.token,
        "session_id": session_id or None,
        "status": DocumentSign.STATUS_EXPIRED,
    }


def log_signing_callback(payload, *, success, status_code, error_message="", response_payload=None):
    IntegrationRequestLog.objects.create(
        provider=PROVIDER,
        direction=IntegrationRequestLog.DIRECTION_INBOUND,
        method="POST",
        endpoint=CALLBACK_ENDPOINT,
        request_payload=payload,
        response_payload=response_payload or {"success": success},
        status_code=status_code,
        success=success,
        error_message=error_message,
        object_type="document_sign_signing_session",
        object_id=str(payload.get("session_id") or payload.get("external_reference") or ""),
    )
