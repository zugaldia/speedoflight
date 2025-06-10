import base64
import uuid
from typing import Optional

from gi.repository import GdkPixbuf  # type: ignore


def generate_uuid() -> str:
    return str(uuid.uuid4())


def is_empty(text: Optional[str]) -> bool:
    return not text or not text.strip()


def base64_to_pixbuf(base64_data: str, mime_type: str) -> Optional[GdkPixbuf.Pixbuf]:
    try:
        # Extract format from MIME type (e.g., "image/png" -> "png")
        image_format = mime_type.split("/")[-1].lower()
        image_data = base64.b64decode(base64_data)
        loader = GdkPixbuf.PixbufLoader.new_with_type(image_format)
        loader.write(image_data)
        loader.close()
        return loader.get_pixbuf()
    except Exception:
        return None
