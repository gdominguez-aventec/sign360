import logging

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from documentmanager.models import (
    DocumentSign,
    DocumentSignSignature,
    DocumentSignSigner,
)
from documentmanager.utils.document_sign_config import (
    DOCUMENT_SIGN_REFERENCE_PREFIX,
    LEGACY_REFERENCE_PREFIXES,
)
from documentmanager.utils.main_utils import get_default_service, upload_document
from integrations.models import IntegrationRequestLog, SigningSession
from integrations.outbound.signing.client import SigningClient
from integrations.outbound.signing.exceptions import SigningApiError

logger = logging.getLogger(__name__)

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


def _resolve_signer(external_reference):
    ref = (external_reference or "").strip()
    if not ref:
        return None
    for prefix in (DOCUMENT_SIGN_REFERENCE_PREFIX, *LEGACY_REFERENCE_PREFIXES):
        if ref.startswith(prefix):
            ref = ref[len(prefix):]
            break
    signer = DocumentSignSigner.objects.filter(token=ref).first()
    if signer:
        return signer
    if ref.isdigit():
        return DocumentSignSigner.objects.filter(id=int(ref)).first()
    return None


def _signed_provider_documents(payload):
    """Els documents del payload que el proveïdor marca com a firmats."""
    return [
        document
        for document in (payload.get("documents") or [])
        if isinstance(document, dict) and document.get("signed") and document.get("id")
    ]


def _resolve_sign_document(signer, session, provider_document, index):
    """
    Tradueix l'id de document del proveïdor al nostre `DocumentSignDocument`.

    Primer pel mapa que vam desar en crear la sessió; si no hi és (perquè el
    proveïdor no ens va retornar la llista de documents), per l'ordre en què els
    vam enviar, que és el mateix ordre amb què els guardem.
    """
    sign_documents = list(signer.document_sign.documents.all())
    if not sign_documents:
        return None

    if session:
        mapped_id = (session.document_map or {}).get(str(provider_document.get("id")))
        if mapped_id:
            match = next((item for item in sign_documents if item.id == mapped_id), None)
            if match:
                return match

    if index < len(sign_documents):
        return sign_documents[index]
    return None


def _store_signed_document(sign_document, signer, pdf_bytes):
    """
    Desa el PDF firmat com una **versió nova** del document, sense tocar cap de
    les anteriors: l'original es conserva sempre i cada signant hi afegeix un
    graó a la cadena.
    """
    previous = sign_document.current_document
    base_name = (sign_document.original_document.document_name or "document.pdf").rsplit(".", 1)[0]
    filename = f"{base_name}_signat_{signer.order}.pdf"

    file_obj = SimpleUploadedFile(filename, pdf_bytes, content_type="application/pdf")
    document = upload_document(
        file_obj,
        "DOCUMENT_SIGN",
        entity_id=signer.document_sign_id,
        entity_token=signer.document_sign.token,
        folder="signed",
        document_name=filename,
        service=get_default_service(),
        content_type="application/pdf",
        version=previous.version + 1,
        parent_document=previous,
    )

    sign_document.current_document = document
    sign_document.save(update_fields=["current_document"])

    DocumentSignSignature.objects.update_or_create(
        signer=signer,
        sign_document=sign_document,
        defaults={"document": document},
    )
    return document


def _download_signed_pdf(session_id, provider_document):
    if not session_id:
        return None
    try:
        return SigningClient().download_signed_document(session_id, provider_document["id"])
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

    signer = _resolve_signer(external_reference)
    if not signer:
        raise SigningCallbackError(
            "No s'ha trobat cap signant amb aquesta referència.", status_code=404
        )

    if event == "session.expired":
        return _handle_expired(signer, session_id)
    return _handle_signed(signer, session_id, payload)


def _handle_signed(signer, session_id, payload):
    document_sign = signer.document_sign
    signed_at = _parse_signed_at(payload.get("signed_at"))
    session = SigningSession.objects.filter(session_id=session_id).first() if session_id else None

    provider_documents = _signed_provider_documents(payload)
    if not provider_documents:
        raise SigningCallbackError(
            "El webhook no indica cap document firmat.", status_code=400
        )

    stored = []
    for index, provider_document in enumerate(provider_documents):
        sign_document = _resolve_sign_document(signer, session, provider_document, index)
        if not sign_document:
            raise SigningCallbackError(
                f"No s'ha pogut identificar el document {provider_document.get('id')} de la sessió.",
                status_code=400,
            )

        pdf_bytes = _download_signed_pdf(session_id, provider_document)
        if not pdf_bytes:
            raise SigningCallbackError(
                "No s'ha pogut descarregar el document firmat del servei de signatura.",
                status_code=400,
            )

        stored.append(_store_signed_document(sign_document, signer, pdf_bytes).id)

    signer.status = DocumentSignSigner.STATUS_SIGNED
    signer.signed_at = signed_at
    signer.error_report = None
    signer.save(update_fields=["status", "signed_at", "error_report"])

    if session:
        session.status = SigningSession.STATUS_SIGNED
        session.signed_at = signed_at
        session.save(update_fields=["status", "signed_at", "updated_at"])

    next_signer, next_error = _advance_chain(document_sign, signed_at)

    return {
        "ok": True,
        "document_sign_id": document_sign.id,
        "document_sign_token": document_sign.token,
        "signer_id": signer.id,
        "signer_order": signer.order,
        "session_id": session_id or None,
        "documents_saved": stored,
        "next_signer_id": next_signer.id if next_signer else None,
        "next_signer_error": next_error,
    }


def _advance_chain(document_sign, signed_at):
    """
    Passa el torn al signant següent obrint-li la sessió, o tanca la sol·licitud
    si ja han firmat tots.

    Si obrir la sessió següent falla, la signatura que acabem de rebre **no** es
    desfà: queda desada i la sol·licitud en estat d'error perquè es pugui
    reintentar l'enviament sense perdre res.
    """
    from integrations.outbound.signing.services import create_signer_session

    if document_sign.all_signed():
        document_sign.status = DocumentSign.STATUS_SIGNED
        document_sign.signed_at = signed_at
        document_sign.error_report = None
        document_sign.save(
            update_fields=["status", "signed_at", "error_report", "updated_at"]
        )
        return None, None

    next_signer = document_sign.next_pending_signer()
    if not next_signer:
        return None, None

    try:
        create_signer_session(next_signer)
    except SigningApiError as exc:
        logger.warning(
            "No s'ha pogut enviar la sol·licitud %s al signant següent", document_sign.id
        )
        return next_signer, str(exc)

    return next_signer, None


def _handle_expired(signer, session_id):
    session = SigningSession.objects.filter(session_id=session_id).first() if session_id else None
    if session and session.status != SigningSession.STATUS_SIGNED:
        session.status = SigningSession.STATUS_EXPIRED
        session.save(update_fields=["status", "updated_at"])

    if signer.status != DocumentSignSigner.STATUS_SIGNED:
        signer.status = DocumentSignSigner.STATUS_EXPIRED
        signer.error_report = None
        signer.save(update_fields=["status", "error_report"])

    document_sign = signer.document_sign
    if document_sign.status != DocumentSign.STATUS_SIGNED:
        document_sign.status = DocumentSign.STATUS_EXPIRED
        document_sign.save(update_fields=["status", "updated_at"])

    return {
        "ok": True,
        "document_sign_id": document_sign.id,
        "document_sign_token": document_sign.token,
        "signer_id": signer.id,
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
