import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio  # type: ignore  # noqa: E402

from speedoflight.constants import APPLICATION_ID  # noqa: E402
from speedoflight.services.agent.agent_service import AgentService  # noqa: E402
from speedoflight.services.configuration.configuration_service import (  # noqa: E402
    ConfigurationService,
)
from speedoflight.services.orchestrator.orchestrator_service import OrchestratorService  # noqa: E402
from speedoflight.ui.main.main_window import MainWindow  # noqa: E402


class SolApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APPLICATION_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

        logging.basicConfig(level=logging.INFO)
        self._logger = logging.getLogger(__name__)
        self._logger.info("Initialized.")

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._logger.info("Starting up.")
        self._create_action("quit", self.quit, ["<primary>q"])

        # Currently, the stylesheet only supports dark mode
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

        # Poor man DI
        self._configuration = ConfigurationService()
        self._agent = AgentService(configuration=self._configuration)
        self._orchestrator = OrchestratorService(
            configuration=self._configuration, agent=self._agent
        )

        # Main window
        self._main_window = MainWindow(
            application=self, orchestrator=self._orchestrator
        )

    def do_activate(self):
        self._logger.info("Activating.")
        self._main_window.present()

    def do_shutdown(self):
        self._logger.info("Shutting down.")
        self._orchestrator.shutdown()
        self._agent.shutdown()
        self._configuration.shutdown()
        Adw.Application.do_shutdown(self)

    def _create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)
