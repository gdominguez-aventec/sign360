"""
Comprovacions sobre PDF. El segellat amb certificat (pyHanko) és opcional: si
no hi ha `PFX_PATH` configurat, `seal_pdf` retorna el PDF tal com ha arribat.
"""

import logging
from io import BytesIO

from django.conf import settings
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def is_pdf(file_obj):
    try:
        file_obj.seek(0)
        header = file_obj.read(5)
        file_obj.seek(0)
        return header == b"%PDF-"
    except Exception:
        return False


def count_pages(pdf_bytes):
    try:
        return len(PdfReader(BytesIO(pdf_bytes)).pages)
    except Exception as exc:
        logger.warning("No s'han pogut comptar les pàgines del PDF", exc_info=exc)
        return None


def is_signed_pdf(pdf_bytes):
    """Retorna True si el PDF ja porta algun camp de signatura omplert."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        root = reader.trailer["/Root"]
        if "/AcroForm" not in root:
            return False
        fields = reader.get_fields() or {}
        return any(value.get("/FT") == "/Sig" for value in fields.values())
    except Exception as exc:
        logger.warning("Error comprovant la signatura del PDF", exc_info=exc)
        return False


def seal_pdf(pdf_bytes):
    """
    Segella el PDF amb el certificat del servidor (PAdES). Si no hi ha
    certificat configurat o el segellat falla, es retorna el PDF original: el
    segell és una garantia addicional, no pot fer caure el flux de signatura.
    """
    cert_path = getattr(settings, "PFX_PATH", "")
    cert_password = getattr(settings, "PFX_PASS", "")
    if not cert_path:
        return pdf_bytes

    try:
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
        from pyhanko.sign import signers
        from pyhanko.sign.fields import SigSeedSubFilter
        from pyhanko_certvalidator import ValidationContext

        signer = signers.SimpleSigner.load_pkcs12(
            cert_path, passphrase=cert_password.encode("utf-8") if cert_password else None
        )
        signature_meta = signers.PdfSignatureMetadata(
            field_name="AppAqua360SignSeal",
            md_algorithm="sha256",
            subfilter=SigSeedSubFilter.PADES,
            validation_context=ValidationContext(allow_fetching=True),
            embed_validation_info=True,
            use_pades_lta=True,
        )
        writer = IncrementalPdfFileWriter(BytesIO(pdf_bytes))
        output = signers.sign_pdf(writer, signer=signer, signature_meta=signature_meta)
        output.seek(0)
        return output.read()
    except Exception as exc:
        logger.warning("No s'ha pogut segellar el PDF amb el certificat", exc_info=exc)
        return pdf_bytes
