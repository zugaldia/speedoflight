"""

Implementation of the XDG Desktop Portal Screenshot interface.

https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Screenshot.html

"""

import base64
import os
from typing import Optional

from gi.repository import Gdk, GdkPixbuf, Gio, GLib  # type: ignore

from speedoflight.constants import PNG_FORMAT
from speedoflight.models import DesktopPoint
from speedoflight.services.desktop.base_interface import BaseInterface
from speedoflight.utils import get_data_path

DBUS_INTERFACE_SCREENSHOT = "org.freedesktop.portal.Screenshot"
DBUS_METHOD_SCREENSHOT = "Screenshot"


class ScreenshotInterface(BaseInterface):
    def __init__(self):
        super().__init__(service_name="screenshot")
        self._proxy: Optional[Gio.DBusProxy] = None
        self._logger.info("Initialized.")

    async def _get_screenshot_proxy(self) -> Gio.DBusProxy:
        if self._proxy is None:
            self._proxy = await self._build_proxy(
                interface_name=DBUS_INTERFACE_SCREENSHOT
            )
        return self._proxy

    async def take_screenshot(
        self,
        is_multi_monitor: bool,
        target_monitor: Optional[Gdk.Monitor],
        target_size: DesktopPoint,
    ):
        try:
            encoded = await self._take_screenshot(
                is_multi_monitor=is_multi_monitor,
                target_monitor=target_monitor,
                target_size=target_size,
            )
            return (False, encoded)
        except Exception as e:
            return (True, f"Error taking screenshot: {e}")

    async def _take_screenshot(
        self,
        is_multi_monitor: bool,
        target_monitor: Optional[Gdk.Monitor],
        target_size: DesktopPoint,
    ) -> str:
        """Take a screenshot using the D-Bus interface and return as base64 PNG."""
        file_path = await self._take_dbus_screenshot()
        if not file_path:
            raise RuntimeError("The desktop portal did not return a screenshot URI.")

        if file_path.startswith("file://"):
            file_path = file_path[len("file://") :]

        if not file_path.lower().endswith(f".{PNG_FORMAT}"):
            raise RuntimeError(f"Expected PNG file, got: {file_path}")

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(file_path)
        if pixbuf is None:
            raise RuntimeError(f"Failed to load screenshot from disk: {file_path}")

        # Crop screenshot to the target monitor if needed
        if is_multi_monitor and target_monitor:
            geometry = target_monitor.get_geometry()
            pixbuf = pixbuf.new_subpixbuf(
                geometry.x, geometry.y, geometry.width, geometry.height
            )

        # Scale screenshot if needed
        current_width = pixbuf.get_width()
        current_height = pixbuf.get_height()
        target_width = target_size.x
        target_height = target_size.y
        if current_width != target_width or current_height != target_height:
            pixbuf = pixbuf.scale_simple(
                target_width, target_height, GdkPixbuf.InterpType.BILINEAR
            )

        # Convert to base64 PNG
        success, buffer = pixbuf.save_to_bufferv(PNG_FORMAT)  # type: ignore
        if not success:
            raise RuntimeError("Failed to convert pixbuf to PNG buffer")

        # Clean up the temporary screenshot file
        # TODO: Eventually, it would be good to move this file instead of
        # deleting it to the same location where we are saving the history
        # of the conversation so that there is a record of the visual
        # interactions as well.
        if os.path.exists(file_path):
            os.remove(file_path)

        return base64.b64encode(buffer).decode("utf-8")

    async def _take_dbus_screenshot(self) -> str | None:
        """
        Take a screenshot using the DBus interface:
        https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Screenshot.html
        """
        try:
            parent_window: str = ""
            options = {
                "handle_token": GLib.Variant("s", self._generate_handle_token()),
                "interactive": GLib.Variant("b", False),
            }
            parameters = GLib.Variant("(sa{sv})", (parent_window, options))
            proxy = await self._get_screenshot_proxy()
            result = await self._call_method(
                proxy=proxy,
                method_name=DBUS_METHOD_SCREENSHOT,
                parameters=parameters,
            )

            # Sample URI: file:///home/user/Pictures/Screenshot.png
            self._logger.info(f"Screenshot result: {result}")
            object_path = result[0]
            _, response = await self._get_response(object_path)
            screenshot_uri = response.get("uri", None) if response else None  # type: ignore
            return screenshot_uri
        except Exception as e:
            self._logger.error(f"Failed to take screenshot: {e}")
            return None
