from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


async def save_upload(file: UploadFile, upload_dir: Path, photo_id: str) -> Path:
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("仅支持 JPG、PNG、WEBP 格式。")

    content = await file.read()
    if not content:
        raise ValueError("上传的照片为空。")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("照片不能超过 10 MB。")

    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"{photo_id}{extension}"
    target.write_bytes(content)

    try:
        with Image.open(target) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        target.unlink(missing_ok=True)
        raise ValueError("文件不是有效的图片。") from exc

    return target

