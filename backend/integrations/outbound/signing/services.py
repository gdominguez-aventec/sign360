from django.conf import settings
from django.utils.dateparse import parse_datetime

from documentmanager.models import DocumentSign
from documentmanager.utils.document_sign_config import (
    build_external_reference,
    is_document_sign_enabled,
)
from documentmanager.utils.main_utils import download_document
from integrations.models import SigningSession

from .client import SigningClient
from .exceptions import SigningApiError

OBJECT_TYPE = "document_sign"


def _resolve_callback_url(callback_url=None):
    if callback_url:
        return callback_url
    default_url = getattr(settings, "SIGNING_CALLBACK_URL", "")
    if default_url:
        return default_url
    raise SigningApiError("Falta la URL de callback per a la signatura")


def _resolve_recipient(document_sign, recipient_name=None, recipient_email=None, recipient_phone=None):
    name = recipient_name or document_sign.otp_name
    email = recipient_email or document_sign.otp_email
    phone = recipient_phone or document_sign.otp_phone

    if not name:
        raise SigningApiError("Falta el nom del signant")
    if not email:
        raise SigningApiError("Falta el correu del signant")

    return name, email, phone


def create_document_sign_session(
    document_sign,
    *,
    recipient_name=None,
    recipient_email=None,
    recipient_phone=None,
    callback_url=None,
    force=False,
):
    """
    Obre una sessió de signatura per a `document_sign` i deixa la sol·licitud en
    estat SENDED. Si ja està firmada no es torna a enviar (llevat de `force`),
    perquè una segona sessió invalidaria el PDF que ja tenim guardat.
    """
    if not is_document_sign_enabled():
        raise SigningApiError(
            "El servei de signatura no està configurat (SIGNING_BASE_URL / SIGNING_API_KEY)"
        )

    if document_sign.status == DocumentSign.STATUS_SIGNED and not force:
        raise SigningApiError("Aquest document ja està firmat")

    if not document_sign.document_file:
        raise SigningApiError("La sol·licitud no té cap document associat")

    pdf_bytes = download_document(document_sign.document_file)
    if not pdf_bytes:
        raise SigningApiError("No s'ha pogut llegir el document a firmar")

    name, email, phone = _resolve_recipient(
        document_sign, recipient_name, recipient_email, recipient_phone
    )
    resolved_callback = _resolve_callback_url(callback_url)
    external_reference = build_external_reference(document_sign)
    filename = document_sign.document_file.document_name or f"{document_sign.token}.pdf"

    try:
        result = SigningClient().create_session(
            recipient_name=name,
            recipient_email=email,
            recipient_phone=phone,
            documents=[(filename, pdf_bytes, "application/pdf")],
            external_reference=external_reference,
            callback_url=resolved_callback,
            document_metadata={"title": document_sign.title or filename},
            object_type=OBJECT_TYPE,
            object_id=str(document_sign.id),
        )
    except SigningApiError as exc:
        document_sign.status = DocumentSign.STATUS_ERROR
        document_sign.error_report = str(exc)[:255]
        document_sign.save(update_fields=["status", "error_report", "updated_at"])
        raise

    session_id = (result.get("session_id") or result.get("id") or "").strip()
    if not session_id:
        message = "El servei de signatura no ha retornat cap identificador de sessió"
        document_sign.status = DocumentSign.STATUS_ERROR
        document_sign.error_report = message
        document_sign.save(update_fields=["status", "error_report", "updated_at"])
        raise SigningApiError(message)

    session, _ = SigningSession.objects.update_or_create(
        session_id=session_id,
        defaults={
            "document_sign": document_sign,
            "external_reference": external_reference,
            "status": SigningSession.STATUS_PENDING,
            "signing_url": result.get("signing_url") or "",
            "recipient_name": name,
            "recipient_email": email,
            "recipient_phone": phone or "",
            "callback_url": resolved_callback,
            "email_sent": bool(result.get("email_sent", True)),
            "expires_at": parse_datetime(result.get("expires_at") or "") or None,
        },
    )

    document_sign.status = DocumentSign.STATUS_SENDED
    document_sign.error_report = None
    document_sign.otp_name = name
    document_sign.otp_email = email
    document_sign.otp_phone = phone or ""
    document_sign.save(
        update_fields=[
            "status",
            "error_report",
            "otp_name",
            "otp_email",
            "otp_phone",
            "updated_at",
        ]
    )

    return session
