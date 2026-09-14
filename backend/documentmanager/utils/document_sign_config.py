from django.conf import settings

# Prefix per a l'`external_reference` de les sessions de signatura, per evitar
# col·lisions amb l'id numèric de qualsevol altra entitat que el proveïdor
# pugui fer servir com a referència.
DOCUMENT_SIGN_REFERENCE_PREFIX = "docsign-"


def build_external_reference(document_sign):
    """
    Referència que s'envia al proveïdor. Es fa servir el token (opac i únic) i
    no l'id, perquè viatja per correu fins al signant.
    """
    return f"{DOCUMENT_SIGN_REFERENCE_PREFIX}{document_sign.token}"


def is_document_sign_enabled():
    """
    La signatura via API externa només està disponible si hi ha URL i clau
    configurades; si no, les vistes retornen un error explícit en lloc de
    fallar dins del client HTTP.
    """
    return bool(getattr(settings, "SIGNING_BASE_URL", "")) and bool(
        getattr(settings, "SIGNING_API_KEY", "")
    )
