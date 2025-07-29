from typing import Optional

from gi.repository import Gdk  # type: ignore
from mcp import types
from pydantic import BaseModel

from speedoflight.models import (
    MessageRole,
    RequestMessage,
    ToolInputResponse,
    ToolTextOutputRequest,
)
from speedoflight.services.base_service import BaseService


class DesktopToolResult(BaseModel):
    content: str
    is_error: bool


class DesktopService(BaseService):
    SERVICE_NAME = "desktop"

    def __init__(self):
        super().__init__(service_name=self.SERVICE_NAME)
        self._clipboard: Optional[Gdk.Clipboard] = None
        self._setup_clipboard()
        self._logger.info("Initialized.")

    def shutdown(self) -> None:
        self._clipboard = None

    def _setup_clipboard(self) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            self._logger.warning(
                "Failed to get default GDK display, clipboard will not work."
            )
            return

        self._clipboard = display.get_clipboard()
        if self._clipboard is None:
            self._logger.warning(
                "Failed to get GNOME clipboard, clipboard will not work."
            )

    def is_tool(self, tool_name: str) -> bool:
        """Check if the given tool name is a desktop tool."""
        return tool_name in ["clipboard_get", "clipboard_set"]

    def get_tools(self) -> list[types.Tool]:
        return [
            types.Tool(
                name="clipboard_get",
                description="Get the current text content of the system clipboard. "
                "This returns the text that was most recently copied or cut to the clipboard.",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="clipboard_set",
                description="Set the content of the system clipboard to the provided text. "
                "This will replace any existing clipboard content and make the text available for pasting in other applications.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text content to copy to the clipboard. "
                            "Can be plain text, code, or any string data.",
                        }
                    },
                    "required": ["text"],
                },
            ),
        ]

    async def call_tool(self, tool_input: ToolInputResponse) -> RequestMessage:
        """Call the specified desktop tool with the provided input."""
        tool_result = DesktopToolResult(is_error=False, content="")

        try:
            if tool_input.name == "clipboard_get":
                tool_result = await self._clipboard_get()
            elif tool_input.name == "clipboard_set":
                if not tool_input.arguments or "text" not in tool_input.arguments:
                    raise ValueError("Missing 'text' input for `clipboard_set` tool.")
                text = tool_input.arguments["text"]
                tool_result = self._clipboard_set(text)
            else:
                tool_result.is_error = True
                tool_result.content = f"Unknown desktop tool: {tool_input.name}"
        except Exception as e:
            tool_result.is_error = True
            tool_result.content = (
                f"Error executing desktop tool '{tool_input.name}': {e}"
            )

        return RequestMessage(
            role=MessageRole.TOOL,
            content=[
                ToolTextOutputRequest(
                    call_id=tool_input.call_id,
                    name=tool_input.name,
                    text=tool_result.content,
                    is_error=tool_result.is_error,
                )
            ],
        )

    async def _clipboard_get(self) -> DesktopToolResult:
        try:
            if self._clipboard is None:
                return DesktopToolResult(
                    is_error=True, content="Clipboard is not available."
                )

            # If the callback parameter of a Gio asynchronous function is
            # omitted, PyGObject automatically returns an awaitable object
            text = await self._clipboard.read_text_async()  # type: ignore
            content = f"Clipboard content: {text}" if text else "(Clipboard is empty.)"
            return DesktopToolResult(is_error=False, content=content)
        except Exception as e:
            return DesktopToolResult(
                is_error=True, content=f"Error reading clipboard: {e}"
            )

    def _clipboard_set(self, text: str) -> DesktopToolResult:
        try:
            if self._clipboard is None:
                return DesktopToolResult(
                    is_error=True, content="Clipboard is not available."
                )
            self._clipboard.set(text)
            return DesktopToolResult(
                is_error=False, content="Clipboard content set successfully."
            )
        except Exception as e:
            return DesktopToolResult(
                is_error=True, content=f"Error setting clipboard: {e}"
            )
