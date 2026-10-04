import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from docx import Document
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".docx", ".txt", ".json"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


async def save_material(file: UploadFile, upload_dir: Path) -> dict[str, Any]:
    filename = Path(file.filename or "unknown").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("支持 JPG、PNG、WEBP、PDF、DOCX、TXT、JSON 文件。")
    content = await file.read()
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("文件不能为空且不能超过 20 MB。")
    material_id = str(uuid4())
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"{material_id}{extension}"
    target.write_bytes(content)
    if extension in {".jpg", ".jpeg", ".png", ".webp"}:
        try:
            with Image.open(target) as image:
                image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            target.unlink(missing_ok=True)
            raise ValueError("文件不是有效的图片。") from exc
    text = extract_text(target, extension)
    file_type = "image" if extension in {".jpg", ".jpeg", ".png", ".webp"} else extension[1:]
    return {"material_id": material_id, "filename": filename, "file_type": file_type, "stored_path": str(target), "content": {"text": text, "image_available": file_type == "image"}}


def extract_text(path: Path, extension: str) -> str:
    if extension == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if extension == ".json":
        return json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False)
    if extension == ".pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    if extension == ".docx":
        return "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)
    return ""
