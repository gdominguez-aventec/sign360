import os
import uuid

from django.conf import settings


def _target_dir(folder):
    base = settings.DOCUMENT_STORAGE_PATH
    path = os.path.join(base, folder) if folder else base
    os.makedirs(path, exist_ok=True)
    return path


def save_file(file_obj, folder, filename):
    """
    Desa `file_obj` al disc i retorna la ruta absoluta resultant.

    El nom es prefixa amb un uuid curt perquè dues pujades amb el mateix nom no
    es trepitgin; el nom original es conserva a `Document.document_name`.
    """
    directory = _target_dir(folder)
    stored_name = f"{uuid.uuid4().hex[:12]}_{filename}"
    full_path = os.path.join(directory, stored_name)

    file_obj.seek(0)
    with open(full_path, "wb") as destination:
        for chunk in file_obj.chunks() if hasattr(file_obj, "chunks") else [file_obj.read()]:
            destination.write(chunk)

    return full_path


def read_file(location):
    with open(location, "rb") as source:
        return source.read()


def delete_file(location):
    if location and os.path.exists(location):
        os.remove(location)
        return True
    return False
