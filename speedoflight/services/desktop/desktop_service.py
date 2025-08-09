import asyncio
from typing import Optional

from gi.repository import Gdk  # type: ignore
from mcp import types

from speedoflight.constants import (
    MAX_IMAGE_SIZE,
    TOOL_CLIPBOARD_GET_NAME,
    TOOL_CLIPBOARD_SET_NAME,
    TOOL_COMPUTER_USE_NAME,
)
from speedoflight.models import (
    DesktopPoint,
    ImageMimeType,
    MessageRole,
    RequestMessage,
    ToolImageOutputRequest,
    ToolInputResponse,
    ToolTextOutputRequest,
)
from speedoflight.services.base_service import BaseService
from speedoflight.services.configuration import ConfigurationService
from speedoflight.services.desktop.clipboard_service import ClipboardService
from speedoflight.services.desktop.remote_interface import RemoteInterface
from speedoflight.services.desktop.screenshot_interface import ScreenshotInterface
from speedoflight.services.desktop.xdotool_service import XdotoolService
from speedoflight.utils import is_empty


class DesktopService(BaseService):
    def __init__(self, configuration: ConfigurationService):
        super().__init__(service_name="desktop")
        self._configuration = configuration
        self._dotool = XdotoolService()
        self._remote = RemoteInterface()
        self._screenshot = ScreenshotInterface()

        self._is_multi_monitor = False
        self._target_monitor: Optional[Gdk.Monitor] = None
        self._target_size = DesktopPoint(x=0, y=0)

        display = Gdk.Display.get_default()
        if not display:
            raise RuntimeError("No display found. Is the desktop environment running?")

        self._setup(display=display)
        self._clipboard = ClipboardService(display=display)
        self._logger.info("Initialized.")

    def shutdown(self) -> None:
        pass

    def _setup(self, display: Gdk.Display) -> None:
        """Initial setup for the desktop service."""
        try:
            self._get_monitors_info(display)
            self._get_target_size()
        except Exception as e:
            raise RuntimeError(f"Failed to setup desktop service: {e}") from e

    def _get_monitors_info(self, display: Gdk.Display):
        monitors = [
            monitor
            for monitor in display.get_monitors()
            if isinstance(monitor, Gdk.Monitor)
        ]

        if len(monitors) == 0:
            # We expect at least one monitor to be available
            raise RuntimeError("No monitors found in the current display.")

        self._target_monitor = monitors[0]
        self._is_multi_monitor = len(monitors) > 1
        if not self._is_multi_monitor:
            return

        if self._configuration.config.target_monitor:
            for monitor in monitors:
                # We assume the connector is a stable string as long as
                # the monitor physical setup doesn't change. Or is there a
                # better way to ID a monitor?
                if monitor.get_connector() == self._configuration.config.target_monitor:
                    self._target_monitor = monitor
                    self._logger.info(f"Monitor selected: {monitor.get_connector()}")
                    return

        self._logger.info("No target monitor specified or not found, options are:")
        for monitor in monitors:
            geometry: Gdk.Rectangle = monitor.get_geometry()
            self._logger.info(
                f"- Monitor ID {monitor.get_connector()} "
                f"({geometry.width}x{geometry.height}): "
                f"Position ({geometry.x}, {geometry.y})"
            )

    def _get_target_size(self):
        """Determine the best target image size based on current screen aspect ratio."""
        if not self._target_monitor:
            return

        geometry = self._target_monitor.get_geometry()
        screen_width = geometry.width
        screen_height = geometry.height
        if screen_width <= MAX_IMAGE_SIZE and screen_height <= MAX_IMAGE_SIZE:
            # If both dimensions are smaller than the max size, use them directly
            self._target_size = DesktopPoint(x=screen_width, y=screen_height)
            return

        aspect_ratio = screen_width / screen_height
        if aspect_ratio >= 1:  # Landscape or square
            target_width = MAX_IMAGE_SIZE
            target_height = int(MAX_IMAGE_SIZE / aspect_ratio)
        else:  # Portrait
            target_height = MAX_IMAGE_SIZE
            target_width = int(MAX_IMAGE_SIZE * aspect_ratio)

        self._target_size = DesktopPoint(x=target_width, y=target_height)
        self._logger.info(
            f"Target size set to: {self._target_size.x}x{self._target_size.y}"
        )

    def get_target_size(self) -> tuple[int, int]:
        """Get the target display size for computer use."""
        return (self._target_size.x, self._target_size.y)

    def from_desktop_to_model(self, point: DesktopPoint) -> DesktopPoint:
        """Convert desktop coordinates to model coordinates."""
        if not self._target_monitor:
            return point

        geometry = self._target_monitor.get_geometry()

        x, y = point.x, point.y
        if self._is_multi_monitor:
            x -= geometry.x
            y -= geometry.y

        scale_x = self._target_size.x / geometry.width
        scale_y = self._target_size.y / geometry.height
        model_x = int(x * scale_x)
        model_y = int(y * scale_y)

        return DesktopPoint(x=model_x, y=model_y)

    def from_model_to_desktop(self, point: DesktopPoint) -> DesktopPoint:
        """Convert model coordinates to desktop coordinates."""
        if not self._target_monitor:
            return point

        geometry = self._target_monitor.get_geometry()

        scale_x = geometry.width / self._target_size.x
        scale_y = geometry.height / self._target_size.y
        desktop_x = int(point.x * scale_x)
        desktop_y = int(point.y * scale_y)

        if self._is_multi_monitor:
            desktop_x += geometry.x
            desktop_y += geometry.y

        return DesktopPoint(x=desktop_x, y=desktop_y)

    def is_tool(self, tool_name: str) -> bool:
        """Check if the given tool name is a desktop tool."""
        return tool_name in [
            TOOL_CLIPBOARD_GET_NAME,
            TOOL_CLIPBOARD_SET_NAME,
            TOOL_COMPUTER_USE_NAME,
        ]

    def get_tools(self) -> list[types.Tool]:
        return [
            types.Tool(
                name=TOOL_CLIPBOARD_GET_NAME,
                description="Get the current text content of the system clipboard. "
                "This returns the text that was most recently copied or cut to the clipboard.",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name=TOOL_CLIPBOARD_SET_NAME,
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
        try:
            if tool_input.name == TOOL_CLIPBOARD_GET_NAME:
                tool_result = await self._clipboard.get_text(tool_input)
            elif tool_input.name == TOOL_CLIPBOARD_SET_NAME:
                tool_result = self._clipboard.set_text(tool_input)
            elif tool_input.name == TOOL_COMPUTER_USE_NAME:
                tool_result = await self._handle_computer_use(tool_input)
            else:
                raise ValueError(f"Unknown desktop tool: {tool_input.name}")
        except Exception as e:
            tool_result = ToolTextOutputRequest(
                call_id=tool_input.call_id,
                name=tool_input.name,
                is_error=False,
                text=f"Error executing desktop tool '{tool_input.name}': {e}",
            )

        return RequestMessage(
            role=MessageRole.TOOL,
            content=[tool_result],
        )

    def _validate_args(
        self, action: str, args: dict, required: list[str], optional: list[str]
    ) -> None:
        for required_key in required:
            if required_key not in args:
                raise ValueError(
                    f"Action `{action}` requires a value for the `{required_key}` parameter."
                )

        valid_keys = set(required + optional)
        for arg_key in args:
            if arg_key not in valid_keys:
                self._logger.warning(
                    f"Action `{action}` received an unexpected parameter ({arg_key})."
                )

    def _validate_coordinates(
        self, coordinate: tuple[int, int] | None
    ) -> DesktopPoint | None:
        # Sample value: 'coordinate': [600, 400]
        if coordinate is None:
            return None
        if not isinstance(coordinate, list) or len(coordinate) != 2:
            raise ValueError(f"The `coordinate` parameter must be a tuple of length 2.")
        if not all(isinstance(i, int) and i >= 0 for i in coordinate):
            raise ValueError(f"The `coordinate` parameter must have non-negative ints.")
        return self.from_model_to_desktop(
            DesktopPoint(x=coordinate[0], y=coordinate[1])
        )

    # TODO: Add action delays for some actions?
    # https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/computer-use-tool#follow-implementation-best-practices
    async def _handle_computer_use(
        self, tool_input: ToolInputResponse
    ) -> ToolTextOutputRequest | ToolImageOutputRequest:
        self._logger.info(f"-> Computer use: {tool_input}.")
        is_error = False
        content: str = ""

        # Sample arguments value: {'action': 'left_click', 'coordinate': [600, 400]}
        action = tool_input.arguments.get("action", None)
        args = tool_input.arguments
        args.pop("action", None)
        match action:
            case "screenshot":
                self._validate_args(action, args, [], [])
                is_error, content = await self._screenshot.take_screenshot(
                    is_multi_monitor=self._is_multi_monitor,
                    target_monitor=self._target_monitor,
                    target_size=self._target_size,
                )
            case "wait":
                self._validate_args(action, args, [], ["duration"])
                duration = args.get("duration", 2)
                await asyncio.sleep(duration)
                content = f"Waited for {duration} seconds."
            case "type":
                self._validate_args(action, args, ["text"], [])
                text = args.get("text", None)
                is_error, content = await self._dotool.do_type(text=text)  # type: ignore
            case "key":
                self._validate_args(action, args, ["text"], [])
                text = args.get("text", None)
                is_error, content = await self._dotool.do_key(text=text)  # type: ignore
            case "hold_key":
                self._validate_args(action, args, ["text", "duration"], [])
                text = args.get("text", None)
                duration = args.get("duration", None)
                is_error, content = await self._dotool.do_hold_key(
                    text=text,  # type: ignore
                    duration=duration,  # type: ignore
                )
            case "left_click":
                self._validate_args(action, args, [], ["coordinate", "key"])
                coordinate = self._validate_coordinates(args.get("coordinate", None))
                key = args.get("key", None)
                is_error, content = await self._dotool.do_left_click(
                    coordinate=coordinate, key=key
                )
            case "mouse_move":
                self._validate_args(action, args, ["coordinate"], [])
                coordinate = self._validate_coordinates(args.get("coordinate", None))
                is_error, content = await self._dotool.do_mouse_move(
                    coordinate=coordinate  # type: ignore
                )
            case "scroll":
                self._validate_args(
                    action,
                    args,
                    ["scroll_direction", "scroll_amount"],
                    ["coordinate", "text"],
                )
                direction = args.get("scroll_direction", None)
                amount = args.get("scroll_amount", None)
                coordinate = self._validate_coordinates(args.get("coordinate", None))
                text = args.get("text", None)
                is_error, content = await self._dotool.do_scroll(
                    direction=direction,  # type: ignore
                    amount=amount,  # type: ignore
                    coordinate=coordinate,
                    text=text,
                )
            case "left_click_drag":
                self._validate_args(action, args, ["coordinate"], [])
                coordinate = self._validate_coordinates(args.get("coordinate", None))
                is_error, content = await self._dotool.do_left_click_drag(
                    coordinate=coordinate  # type: ignore
                )
            case "right_click":
                self._validate_args(action, args, [], ["coordinate", "key"])
                coordinate = self._validate_coordinates(args.get("coordinate", None))
                key = args.get("key", None)
                is_error, content = await self._dotool.do_right_click(
                    coordinate=coordinate, key=key
                )
            case "middle_click":
                self._validate_args(action, args, [], ["coordinate", "key"])
                coordinate = self._validate_coordinates(args.get("coordinate", None))
                key = args.get("key", None)
                is_error, content = await self._dotool.do_middle_click(
                    coordinate=coordinate, key=key
                )
            case "double_click":
                self._validate_args(action, args, [], ["coordinate", "key"])
                coordinate = self._validate_coordinates(args.get("coordinate", None))
                key = args.get("key", None)
                is_error, content = await self._dotool.do_double_click(
                    coordinate=coordinate, key=key
                )
            case "triple_click":
                self._validate_args(action, args, [], ["coordinate", "key"])
                coordinate = self._validate_coordinates(args.get("coordinate", None))
                key = args.get("key", None)
                is_error, content = await self._dotool.do_triple_click(
                    coordinate=coordinate, key=key
                )
            case "left_mouse_down":
                self._validate_args(action, args, [], [])
                is_error, content = await self._dotool.do_left_mouse_down()
            case "left_mouse_up":
                self._validate_args(action, args, [], [])
                is_error, content = await self._dotool.do_left_mouse_up()
            case "cursor_position":
                # This one is interesting. First, because it's not in the
                # documentation, but it's in the reference implementation.
                # Second, because it's the only one that requires converting
                # coordinates from real to model.
                self._validate_args(action, args, [], [])
                is_error, result = await self._dotool.do_cursor_position()
                if isinstance(result, DesktopPoint):
                    converted = self.from_desktop_to_model(result)
                    content = f"Cursor position: ({converted.x}, {converted.y})"
                else:
                    content = result
            case _:
                self._logger.warning(f"Unsupported: {tool_input}.")
                is_error = True
                content = (
                    f"Apologies, action {action} is not currently supported. "
                    "Please use a different tool to achieve your goal. "
                    "If this is not possible, stop here and explain the limitation to the user."
                )

        if action == "screenshot" and not is_error:
            return ToolImageOutputRequest(
                call_id=tool_input.call_id,
                name=tool_input.name,
                data=content,
                mime_type=ImageMimeType.PNG,
                is_error=is_error,
            )
        else:
            return ToolTextOutputRequest(
                call_id=tool_input.call_id,
                name=tool_input.name,
                is_error=is_error,
                text=content,
            )
