import asyncio
import uuid
from typing import Optional

from gi.repository import Gio, GLib  # type: ignore

from speedoflight.services.base_service import BaseService

DBUS_NAME_DESKTOP_PORTAL = "org.freedesktop.portal.Desktop"

DBUS_PATH_DESKTOP_PORTAL = "/org/freedesktop/portal/desktop"

DBUS_INTERFACE_REQUEST = "org.freedesktop.portal.Request"
DBUS_INTERFACE_PROPERTIES = "org.freedesktop.DBus.Properties"

DBUS_METHOD_GET = "Get"

# Depending on the request, the portal might present a dialog to the user to
# approve permissions and/or to select the region for a screenshot. Because
# of that, the timeout needs to be a reasonable amount for the user to respond.
RESPONSE_TIMEOUT = 30.0  # seconds


class BaseInterface(BaseService):
    def __init__(self, service_name: str):
        super().__init__(service_name=service_name)

    def _generate_handle_token(self) -> str:
        return f"sol_handle_{uuid.uuid4().hex[:8]}"

    def _generate_session_handle_token(self) -> str:
        return f"sol_session_{uuid.uuid4().hex[:8]}"

    async def _build_proxy(
        self,
        interface_name: str,
        object_path: str = DBUS_PATH_DESKTOP_PORTAL,
    ) -> Gio.DBusProxy:
        return await Gio.DBusProxy.new_for_bus(
            bus_type=Gio.BusType.SESSION,
            flags=Gio.DBusProxyFlags.NONE,
            info=None,
            name=DBUS_NAME_DESKTOP_PORTAL,
            object_path=object_path,
            interface_name=interface_name,
        )  # type: ignore

    async def _call_method(
        self,
        proxy: Gio.DBusProxy,
        method_name: str,
        parameters: Optional[GLib.Variant] = None,
    ) -> GLib.Variant:
        return await proxy.call(
            method_name=method_name,
            parameters=parameters,
            flags=Gio.DBusCallFlags.NONE,
            timeout_msec=int(RESPONSE_TIMEOUT * 1000),
        )  # type: ignore

    async def _get_response(
        self, object_path: str
    ) -> tuple[bool, Optional[GLib.VariantDict]]:
        is_error = False
        response: Optional[GLib.VariantDict] = None
        response_event = asyncio.Event()

        def on_response(
            proxy: Gio.DBusProxy,
            sender_name: str,
            signal_name: str,
            parameters: GLib.Variant,
        ):
            nonlocal is_error, response
            response_code, response = parameters.unpack()
            is_error = response_code != 0
            response_event.set()

        request_proxy: Gio.DBusProxy = await self._build_proxy(
            interface_name=DBUS_INTERFACE_REQUEST,
            object_path=object_path,
        )

        connect_id = request_proxy.connect("g-signal", on_response)
        await asyncio.wait_for(response_event.wait(), timeout=RESPONSE_TIMEOUT)
        request_proxy.disconnect(connect_id)
        return (is_error, response)
