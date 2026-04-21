import shutil

from . import config
from .utils import (
    ImageValidationError,
    person_folder,
    safe_filename,
    validate_image_bytes,
)


def remove_person_folder(category_folder: str, person_id: int, person_name: str) -> bool:
    """Delete dataset/{category_folder}/{id}_{name}/ if it exists. Bounded to
    config.DATASET_DIR — never removes anything outside it."""
    target = (config.DATASET_DIR / category_folder / person_folder(person_id, person_name)).resolve()
    root = config.DATASET_DIR.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return False
    if target.is_dir():
        shutil.rmtree(target)
        return True
    return False


def save_uploads(uploads, category_folder: str, person_id: int, person_name: str):
    """Validate and save uploaded images under dataset/{category_folder}/{id}_{name}/.
    Returns (first_saved_path_or_empty_string, error_message_or_none)."""
    valid = [u for u in (uploads or []) if u and u.filename]
    if not valid:
        return "", None

    target = config.DATASET_DIR / category_folder / person_folder(person_id, person_name)
    target.mkdir(parents=True, exist_ok=True)

    first_path = ""
    for idx, upload in enumerate(valid):
        data = upload.file.read()
        try:
            ext = validate_image_bytes(data, upload.filename)
        except ImageValidationError as e:
            return "", f"{upload.filename}: {e}"
        fname = f"{safe_filename(person_name)}_{person_id}_{idx}{ext}"
        path = target / fname
        path.write_bytes(data)
        if not first_path:
            first_path = str(path)
    return first_path, None
