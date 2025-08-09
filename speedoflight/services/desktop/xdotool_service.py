"""

Reference implementation of the xdotool service for desktop automation:
https://github.com/anthropics/anthropic-quickstarts/blob/main/computer-use-demo/computer_use_demo/tools/computer.py

"""

import shlex
from typing import Optional

from speedoflight.models import DesktopPoint
from speedoflight.services.desktop.command_service import TYPING_DELAY, CommandService

XDOTOOL = "/usr/bin/xdotool"


class XdotoolService(CommandService):
    def __init__(self):
        super().__init__(service_name="xdotool")
        self._logger.info("Initialized.")

    async def do_type(self, text: str) -> tuple[bool, str]:
        """Type text string"""
        try:
            quoted = shlex.quote(text)
            command = f"{XDOTOOL} type --delay {TYPING_DELAY} -- {quoted}"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error typing text: {e}"

    async def do_key(self, text: str) -> tuple[bool, str]:
        """Press key or key combination (e.g., "ctrl+s")"""
        try:
            quoted = shlex.quote(text)
            command = f"{XDOTOOL} key -- {quoted}"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error pressing key: {e}"

    async def do_hold_key(self, text: str, duration: int) -> tuple[bool, str]:
        """Hold a key while performing other actions (duration in seconds)"""
        try:
            quoted = shlex.quote(text)
            command = f"{XDOTOOL} keydown {quoted} sleep {duration} keyup {quoted}"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error holding key: {e}"

    async def do_left_click(
        self, coordinate: Optional[DesktopPoint] = None, key: Optional[str] = None
    ) -> tuple[bool, str]:
        """Click at coordinates [x, y]"""
        try:
            parts = []
            if coordinate:
                parts.append(f"mousemove --sync {coordinate.x} {coordinate.y}")
            if key:
                quoted_key = shlex.quote(key)
                parts.append(f"keydown {quoted_key}")
            parts.append("click 1")
            if key:
                quoted_key = shlex.quote(key)
                parts.append(f"keyup {quoted_key}")
            command = f"{XDOTOOL} {' '.join(parts)}"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error left clicking: {e}"

    async def do_mouse_move(self, coordinate: DesktopPoint) -> tuple[bool, str]:
        """Move cursor to coordinates"""
        try:
            command = f"{XDOTOOL} mousemove --sync {coordinate.x} {coordinate.y}"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error moving mouse: {e}"

    async def do_scroll(
        self,
        direction: str,
        amount: int,
        coordinate: Optional[DesktopPoint],
        text: Optional[str],
    ) -> tuple[bool, str]:
        """Scroll in any direction with amount control"""
        try:
            parts = []
            if coordinate:
                parts.append(f"mousemove --sync {coordinate.x} {coordinate.y}")
            if text:
                quoted_text = shlex.quote(text)
                parts.append(f"keydown {quoted_text}")
            scroll_map = {"up": "4", "down": "5", "left": "6", "right": "7"}
            if direction not in scroll_map:
                return True, f"Invalid scroll direction: {direction}"
            button = scroll_map[direction]
            parts.append(f"click --repeat {amount} {button}")
            if text:
                quoted_text = shlex.quote(text)
                parts.append(f"keyup {quoted_text}")
            command = f"{XDOTOOL} {' '.join(parts)}"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error scrolling: {e}"

    async def do_left_click_drag(self, coordinate: DesktopPoint) -> tuple[bool, str]:
        """Click and drag between coordinates"""
        try:
            command = f"{XDOTOOL} mousedown 1 mousemove --sync {coordinate.x} {coordinate.y} mouseup 1"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error dragging: {e}"

    async def do_right_click(
        self, coordinate: Optional[DesktopPoint] = None, key: Optional[str] = None
    ) -> tuple[bool, str]:
        """Additional mouse buttons"""
        try:
            parts = []
            if coordinate:
                parts.append(f"mousemove --sync {coordinate.x} {coordinate.y}")
            if key:
                quoted_key = shlex.quote(key)
                parts.append(f"keydown {quoted_key}")
            parts.append("click 3")
            if key:
                quoted_key = shlex.quote(key)
                parts.append(f"keyup {quoted_key}")
            command = f"{XDOTOOL} {' '.join(parts)}"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error right clicking: {e}"

    async def do_middle_click(
        self, coordinate: Optional[DesktopPoint] = None, key: Optional[str] = None
    ) -> tuple[bool, str]:
        """Additional mouse buttons"""
        try:
            parts = []
            if coordinate:
                parts.append(f"mousemove --sync {coordinate.x} {coordinate.y}")
            if key:
                quoted_key = shlex.quote(key)
                parts.append(f"keydown {quoted_key}")
            parts.append("click 2")
            if key:
                quoted_key = shlex.quote(key)
                parts.append(f"keyup {quoted_key}")
            command = f"{XDOTOOL} {' '.join(parts)}"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error middle clicking: {e}"

    async def do_double_click(
        self, coordinate: Optional[DesktopPoint] = None, key: Optional[str] = None
    ) -> tuple[bool, str]:
        """Multiple clicks"""
        try:
            parts = []
            if coordinate:
                parts.append(f"mousemove --sync {coordinate.x} {coordinate.y}")
            if key:
                quoted_key = shlex.quote(key)
                parts.append(f"keydown {quoted_key}")
            parts.append("click --repeat 2 --delay 10 1")
            if key:
                quoted_key = shlex.quote(key)
                parts.append(f"keyup {quoted_key}")
            command = f"{XDOTOOL} {' '.join(parts)}"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error double clicking: {e}"

    async def do_triple_click(
        self, coordinate: Optional[DesktopPoint] = None, key: Optional[str] = None
    ) -> tuple[bool, str]:
        """Multiple clicks"""
        try:
            parts = []
            if coordinate:
                parts.append(f"mousemove --sync {coordinate.x} {coordinate.y}")
            if key:
                quoted_key = shlex.quote(key)
                parts.append(f"keydown {quoted_key}")
            parts.append("click --repeat 3 --delay 10 1")
            if key:
                quoted_key = shlex.quote(key)
                parts.append(f"keyup {quoted_key}")
            command = f"{XDOTOOL} {' '.join(parts)}"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error triple clicking: {e}"

    async def do_left_mouse_down(self) -> tuple[bool, str]:
        """Fine-grained click control"""
        try:
            command = f"{XDOTOOL} mousedown 1"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error mouse down: {e}"

    async def do_left_mouse_up(self) -> tuple[bool, str]:
        """Fine-grained click control"""
        try:
            command = f"{XDOTOOL} mouseup 1"
            return await self.execute(command)
        except Exception as e:
            return True, f"Error mouse up: {e}"

    async def do_cursor_position(self) -> tuple[bool, DesktopPoint | str]:
        """Get the current cursor position"""
        try:
            command = f"{XDOTOOL} getmouselocation --shell"
            error, output = await self.execute(command)
            if error:
                return error, output

            # Parse output like "X=123\nY=456\nSCREEN=0\nWINDOW=12345"
            lines = output.strip().split("\n")
            x, y = 0, 0
            for line in lines:
                if line.startswith("X="):
                    x = int(line.split("=")[1])
                elif line.startswith("Y="):
                    y = int(line.split("=")[1])
            return False, DesktopPoint(x=x, y=y)
        except Exception as e:
            return True, f"Error getting cursor position: {e}"
