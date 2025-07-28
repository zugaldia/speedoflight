import logging
from abc import abstractmethod

from gi.repository import GLib, GObject  # type: ignore


class BaseService(GObject.Object):
    def __init__(self, service_name: str):
        super().__init__()
        self._logger = logging.getLogger(service_name)
        self._service_name = service_name

    def safe_emit(self, signal_name: str, *args):
        try:
            # Services use Python asyncio to avoid blocking the UI, which
            # means services should wrap the signal emission in GLib.idle_add
            # to request the main loop to schedule execution in the main thread.
            # https://pygobject.gnome.org/guide/threading.html
            # self._logger.info(f"Emitting signal: {signal_name}")
            GLib.idle_add(self.emit, signal_name, *args)
        except Exception as e:
            self._logger.error(f"Error emitting signal ({signal_name}): {e}")

    @property
    def service_name(self) -> str:
        return self._service_name

    @abstractmethod
    def shutdown(self):
        pass
