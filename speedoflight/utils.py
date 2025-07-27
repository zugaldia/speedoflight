"""

We store all content in XDG directories, which is generally a good practice,
but it's also required to support the sandboxing of Flatpak and Snaps:
https://docs.flatpak.org/en/latest/conventions.html#xdg-base-directories

"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from gi.repository import GLib  # type: ignore
from pydantic import BaseModel

from speedoflight.constants import APPLICATION_ID


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_empty(text: Optional[str]) -> bool:
    return not text or not text.strip()


def safe_json(object: Any) -> str:
    try:
        if isinstance(object, list) and all(
            isinstance(item, BaseModel) for item in object
        ):
            # List of BaseModel objects (e.g. web search results)
            return json.dumps([item.model_dump() for item in object])
        elif isinstance(object, BaseModel):
            return object.model_dump_json()
        else:
            return json.dumps(object)
    except Exception as e:
        return f"Error serializing object to JSON: {e}"


def get_cache_path() -> Path:
    """
    Returns the path to the application's cache directory.
    The directory will be created if it doesn't exist.
    Typically: /home/<user>/.cache/io.speedofsound.App
    """
    cache_path = Path(GLib.get_user_cache_dir()) / APPLICATION_ID
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


def get_config_path() -> Path:
    """
    Returns the path to the application's configuration directory.
    The directory will be created if it doesn't exist.
    Typically: /home/<user>/.config/io.speedofsound.App/
    """

    config_path = Path(GLib.get_user_config_dir()) / APPLICATION_ID
    config_path.mkdir(parents=True, exist_ok=True)
    return config_path


def get_data_path() -> Path:
    """
    Returns the path to the application's data directory.
    The directory will be created if it doesn't exist.
    Typically: /home/<user>/.local/share/io.speedofsound.App/
    """
    data_path = Path(GLib.get_user_data_dir()) / APPLICATION_ID
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path
