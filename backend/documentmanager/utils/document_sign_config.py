from django.conf import settings

# Prefix per a l'`external_reference` de les sessions de signatura, per evitar
# col·lisions amb l'id numèric de qualsevol altra entitat que el proveïdor
# pugui fer servir com a referència.
DOCUMENT_SIGN_REFERENCE_PREFIX = "app-aqua360-sign-"

# Prefix que fèiem servir quan l'aplicació es deia Sign360. Les sessions obertes
# abans del canvi de nom encara el porten, i el webhook les ha de poder resoldre.
LEGACY_REFERENCE_PREFIXES = ("sign360-",)


def build_external_reference(signer):
    """
    Referència que s'envia al proveïdor. Identifica el **signant**, no la
    sol·licitud: com que cada signant té la seva sessió, és l'única manera que
    el webhook sàpiga de quin torn de la cadena està parlant.
    """
    return f"{DOCUMENT_SIGN_REFERENCE_PREFIX}{signer.token}"


def is_document_sign_enabled():
    """
    La signatura via API externa només està disponible si hi ha URL i clau
    configurades; si no, les vistes retornen un error explícit en lloc de
    fallar dins del client HTTP.
    """
    return bool(getattr(settings, "SIGNING_BASE_URL", "")) and bool(
        getattr(settings, "SIGNING_API_KEY", "")
    )
