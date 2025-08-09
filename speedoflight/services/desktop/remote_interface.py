"""

Implementation of the XDG Desktop Portal Remote Desktop interface.

https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html

"""

from typing import Optional

from gi.repository import Gio, GLib  # type: ignore

from speedoflight.services.desktop.base_interface import BaseInterface

DBUS_INTERFACE_REMOTE = "org.freedesktop.portal.RemoteDesktop"
DBUS_METHOD_CREATE_SESSION = "CreateSession"
DBUS_METHOD_SELECT_DEVICES = "SelectDevices"
DBUS_METHOD_START = "Start"

DEVICE_TYPE_KEYBOARD = 1
DEVICE_TYPE_POINTER = 2
DEVICE_TYPE_TOUCHSCREEN = 4  # Unused, but defined for completeness

PERSIST_MODE_DO_NOT_PERSIST = 0
PERSIST_MODE_APP_RUNNING = 1
PERSIST_MODE_UNTIL_REVOKED = 2


class RemoteInterface(BaseInterface):
    def __init__(self):
        super().__init__(service_name="remote")
        self._proxy: Optional[Gio.DBusProxy] = None
        self._session_handle: Optional[str] = None

    async def _get_remote_proxy(self) -> Gio.DBusProxy:
        if self._proxy is not None:
            return self._proxy
        self._proxy = await self._build_proxy(interface_name=DBUS_INTERFACE_REMOTE)
        return self._proxy

    async def _create_session(self) -> str | None:
        try:
            options = {
                "handle_token": GLib.Variant("s", self._generate_handle_token()),
                "session_handle_token": GLib.Variant(
                    "s", self._generate_session_handle_token()
                ),
            }
            parameters = GLib.Variant("(a{sv})", (options,))
            proxy = await self._get_remote_proxy()
            result = await self._call_method(
                proxy=proxy,
                method_name=DBUS_METHOD_CREATE_SESSION,
                parameters=parameters,
            )

            object_path = result[0]
            is_error, response = await self._get_response(object_path)
            self._logger.info(f"Create session response (error={is_error}): {response}")
            session_handle = response.get("session_handle", None) if response else None  # type: ignore
            return session_handle
        except Exception as e:
            self._logger.error(f"Failed to create session: {e}")
            return None

    async def _select_devices(self, session_handle: str) -> bool:
        try:
            types = DEVICE_TYPE_KEYBOARD | DEVICE_TYPE_POINTER
            options = {
                "types": GLib.Variant("u", types),
                "handle_token": GLib.Variant("s", self._generate_handle_token()),
                "persist_mode": GLib.Variant("u", PERSIST_MODE_UNTIL_REVOKED),
            }
            parameters = GLib.Variant("(oa{sv})", (session_handle, options))
            proxy = await self._get_remote_proxy()
            result = await self._call_method(
                proxy=proxy,
                method_name=DBUS_METHOD_SELECT_DEVICES,
                parameters=parameters,
            )

            object_path = result[0]
            is_error, response = await self._get_response(object_path)
            self._logger.info(f"Select devices response (error={is_error}): {response}")
            return is_error
        except Exception as e:
            self._logger.error(f"Failed to select devices: {e}")
            return True

    async def _start(self, session_handle: str) -> bool:
        try:
            options = {
                "handle_token": GLib.Variant("s", self._generate_handle_token()),
            }
            parent_window: str = ""
            parameters = GLib.Variant(
                "(osa{sv})", (session_handle, parent_window, options)
            )
            proxy = await self._get_remote_proxy()
            result = await self._call_method(
                proxy=proxy,
                method_name=DBUS_METHOD_START,
                parameters=parameters,
            )

            object_path = result[0]
            is_error, response = await self._get_response(object_path)
            self._logger.info(f"Start session response (error={is_error}): {response}")
            return is_error
        except Exception as e:
            self._logger.error(f"Failed to start session: {e}")
            return True

    async def get_session_handle(self) -> str | None:
        if self._session_handle:
            return self._session_handle

        self._session_handle = await self._create_session()
        if not self._session_handle:
            return None
        is_error = await self._select_devices(self._session_handle)
        if is_error:
            return None
        is_error = await self._start(self._session_handle)
        if is_error:
            return None

        self._logger.info(f"Remote session started with handle: {self._session_handle}")
        return self._session_handle
