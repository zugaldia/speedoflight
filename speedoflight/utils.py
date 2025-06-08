import uuid
from typing import Optional


def generate_uuid() -> str:
    return str(uuid.uuid4())


def is_empty(text: Optional[str]) -> bool:
    return not text or not text.strip()
