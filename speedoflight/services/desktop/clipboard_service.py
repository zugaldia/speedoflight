"""

Eventually this should be another clipboard interface that uses the remote
desktop interface for clipboard communication:

https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Clipboard.html

"""

from typing import Optional

from gi.repository import Gdk  # type: ignore

from speedoflight.constants import TOOL_CLIPBOARD_SET_NAME
from speedoflight.models import ToolInputResponse, ToolTextOutputRequest
from speedoflight.services.base_service import BaseService


class ClipboardService(BaseService):
    def __init__(self, display: Gdk.Display):
        super().__init__(service_name="clipboard")
        self._clipboard: Optional[Gdk.Clipboard] = None
        self._setup_clipboard(display)
        self._logger.info("Initialized.")

    def _setup_clipboard(self, display: Gdk.Display) -> None:
        self._clipboard = display.get_clipboard()
        if self._clipboard is None:
            self._logger.warning(
                "Failed to get GNOME clipboard, clipboard operations will not work."
            )

    async def get_text(self, tool_input: ToolInputResponse) -> ToolTextOutputRequest:
        try:
            if self._clipboard is None:
                raise RuntimeError("Clipboard is not available.")

            # If the callback parameter of a Gio asynchronous function is
            # omitted, PyGObject automatically returns an awaitable object
            text = await self._clipboard.read_text_async()  # type: ignore
            content = (
                f"Clipboard content: <content>{text}</content>"
                if text
                else "(Clipboard is empty.)"
            )
            return ToolTextOutputRequest(
                call_id=tool_input.call_id,
                name=tool_input.name,
                is_error=False,
                text=content,
            )
        except Exception as e:
            return ToolTextOutputRequest(
                call_id=tool_input.call_id,
                name=tool_input.name,
                is_error=True,
                text=f"Error reading clipboard: {e}",
            )

    def set_text(self, tool_input: ToolInputResponse) -> ToolTextOutputRequest:
        try:
            if self._clipboard is None:
                raise RuntimeError("Clipboard is not available.")
            if not tool_input.arguments or "text" not in tool_input.arguments:
                raise ValueError(
                    f"Missing 'text' input in `{TOOL_CLIPBOARD_SET_NAME}` tool."
                )
            text = tool_input.arguments["text"]
            self._clipboard.set(text)
            return ToolTextOutputRequest(
                call_id=tool_input.call_id,
                name=tool_input.name,
                is_error=False,
                text="Clipboard content set successfully.",
            )
        except Exception as e:
            return ToolTextOutputRequest(
                call_id=tool_input.call_id,
                name=tool_input.name,
                is_error=True,
                text=f"Error setting clipboard: {e}",
            )
