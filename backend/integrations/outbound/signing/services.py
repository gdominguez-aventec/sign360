from django.conf import settings
from django.utils.dateparse import parse_datetime

from documentmanager.models import DocumentSign, DocumentSignSigner
from documentmanager.utils.document_sign_config import (
    build_external_reference,
    is_document_sign_enabled,
)
from documentmanager.utils.main_utils import download_document
from integrations.models import SigningSession

from .client import SigningClient
from .exceptions import SigningApiError

OBJECT_TYPE = "document_sign_signer"


def _resolve_callback_url(callback_url=None):
    if callback_url:
        return callback_url
    default_url = getattr(settings, "SIGNING_CALLBACK_URL", "")
    if default_url:
        return default_url
    raise SigningApiError("Falta la URL de callback per a la signatura")


def _collect_documents(document_sign):
    """
    Els documents que s'envien al signant de torn, sempre en la seva versió
    actual: l'original si és el primer signant, o el que ha tornat firmat el
    signant anterior si la cadena ja ha començat.
    """
    documents = []
    sign_documents = list(document_sign.documents.select_related("current_document"))
    if not sign_documents:
        raise SigningApiError("La sol·licitud no té cap document")

    for sign_document in sign_documents:
        current = sign_document.current_document
        content = download_document(current)
        if not content:
            raise SigningApiError(
                f"No s'ha pogut llegir el document «{current.document_name}»"
            )
        documents.append((sign_document, current.document_name, content))

    return documents


def _build_document_map(result, sign_documents):
    """
    Relaciona els ids que el proveïdor assigna als documents amb els nostres.

    El contracte documentat no garanteix el format d'aquesta llista, així que
    s'intenta primer per nom de fitxer i, si el proveïdor no el retorna, per
    l'ordre en què els hem enviat. Si no retorna cap llista, el mapa queda buit
    i el webhook cau a l'ordre com a últim recurs.
    """
    provider_documents = result.get("documents") or []
    document_map = {}

    by_name = {name: sign_document.id for sign_document, name, _ in sign_documents}

    for index, provider_document in enumerate(provider_documents):
        if not isinstance(provider_document, dict):
            continue
        provider_id = provider_document.get("id")
        if provider_id is None:
            continue

        filename = provider_document.get("filename") or provider_document.get("name")
        if filename and filename in by_name:
            document_map[str(provider_id)] = by_name[filename]
        elif index < len(sign_documents):
            document_map[str(provider_id)] = sign_documents[index][0].id

    return document_map


def create_signer_session(signer, *, callback_url=None, force=False):
    """
    Obre la sessió de signatura d'un signant concret amb tots els documents de
    la sol·licitud en la seva versió actual.
    """
    if not is_document_sign_enabled():
        raise SigningApiError(
            "El servei de signatura no està configurat (SIGNING_BASE_URL / SIGNING_API_KEY)"
        )

    document_sign = signer.document_sign

    if signer.status == DocumentSignSigner.STATUS_SIGNED and not force:
        raise SigningApiError(f"El signant {signer.name} ja ha firmat")

    # La cadena és estricta: si un signant anterior encara no ha firmat, el PDF
    # que rebria aquest no portaria la signatura que toca.
    pending_before = document_sign.signers.filter(order__lt=signer.order).exclude(
        status=DocumentSignSigner.STATUS_SIGNED
    )
    if pending_before.exists() and not force:
        previous = pending_before.first()
        raise SigningApiError(
            f"Encara no és el torn de {signer.name}: falta que firmi {previous.name}"
        )

    documents = _collect_documents(document_sign)
    resolved_callback = _resolve_callback_url(callback_url)
    external_reference = build_external_reference(signer)

    try:
        result = SigningClient().create_session(
            recipient_name=signer.name,
            recipient_email=signer.email,
            recipient_phone=signer.phone or None,
            documents=[(name, content, "application/pdf") for _, name, content in documents],
            external_reference=external_reference,
            callback_url=resolved_callback,
            document_metadata={
                "title": document_sign.title or "",
                "signer_order": signer.order,
                "signers_total": document_sign.signers.count(),
            },
            object_type=OBJECT_TYPE,
            object_id=str(signer.id),
        )
    except SigningApiError as exc:
        _mark_error(signer, str(exc))
        raise

    session_id = (result.get("session_id") or result.get("id") or "").strip()
    if not session_id:
        message = "El servei de signatura no ha retornat cap identificador de sessió"
        _mark_error(signer, message)
        raise SigningApiError(message)

    session, _ = SigningSession.objects.update_or_create(
        session_id=session_id,
        defaults={
            "signer": signer,
            "external_reference": external_reference,
            "status": SigningSession.STATUS_PENDING,
            "signing_url": result.get("signing_url") or "",
            "recipient_name": signer.name,
            "recipient_email": signer.email,
            "recipient_phone": signer.phone or "",
            "callback_url": resolved_callback,
            "email_sent": bool(result.get("email_sent", True)),
            "expires_at": parse_datetime(result.get("expires_at") or "") or None,
            "document_map": _build_document_map(result, documents),
        },
    )

    signer.status = DocumentSignSigner.STATUS_SENDED
    signer.error_report = None
    signer.save(update_fields=["status", "error_report"])

    document_sign.status = DocumentSign.STATUS_SENDED
    document_sign.error_report = None
    document_sign.save(update_fields=["status", "error_report", "updated_at"])

    return session


def send_next_signer(document_sign, *, callback_url=None, force=False):
    """
    Envia la sol·licitud al signant que toca. És el punt d'entrada des de les
    vistes: qui crida no ha de saber per quin torn va la cadena.
    """
    signer = document_sign.next_pending_signer()
    if not signer:
        raise SigningApiError("Tots els signants ja han firmat")
    return create_signer_session(signer, callback_url=callback_url, force=force)


def _mark_error(signer, message):
    signer.status = DocumentSignSigner.STATUS_ERROR
    signer.error_report = message[:255]
    signer.save(update_fields=["status", "error_report"])

    document_sign = signer.document_sign
    document_sign.status = DocumentSign.STATUS_ERROR
    document_sign.error_report = message[:255]
    document_sign.save(update_fields=["status", "error_report", "updated_at"])
