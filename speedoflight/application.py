import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio  # type: ignore  # noqa: E402

from speedoflight.constants import APPLICATION_ID, LOG_FILE  # noqa: E402
from speedoflight.services.agent import AgentService  # noqa: E402
from speedoflight.services.configuration import ConfigurationService  # noqa: E402
from speedoflight.services.markdown import MarkdownService  # noqa: E402
from speedoflight.services.mcp import McpService  # noqa: E402
from speedoflight.services.orchestrator import OrchestratorService  # noqa: E402
from speedoflight.ui.main.main_view_model import MainViewModel  # noqa: E402
from speedoflight.ui.main.main_window import MainWindow  # noqa: E402


class SolApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APPLICATION_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

        self._setup_logging()
        self._logger = logging.getLogger(__name__)
        self._logger.info("Initialized.")

    def _setup_logging(self):
        """Setup logging to both console and file."""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.handlers.clear()

        # Console formatter - simpler for interactive use
        console_formatter = logging.Formatter(fmt="%(levelname)s %(name)s: %(message)s")

        # File formatter - more detailed for LLM debugging/troubleshooting
        file_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler - Not only we log more content to this handler, we have
        # it on a file so that we can feed it to the LLM for troubleshooting
        # if anything goes wrong.
        file_handler = logging.FileHandler(LOG_FILE, mode="w")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._logger.info("Starting up.")
        self._create_action("quit", self.quit, ["<primary>q"])

        # Currently, the stylesheet only supports dark mode
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

        # Poor man DI
        self._configuration = ConfigurationService()
        self._markdown = MarkdownService()
        self._mcp = McpService(configuration=self._configuration)
        self._agent = AgentService(configuration=self._configuration, mcp=self._mcp)
        self._orchestrator = OrchestratorService(
            configuration=self._configuration,
            markdown=self._markdown,
            agent=self._agent,
        )

        # View models
        self._main_view_model = MainViewModel(orchestrator=self._orchestrator)

        # Main window
        self._main_window = MainWindow(
            application=self,
            view_model=self._main_view_model,
        )

    def do_activate(self):
        self._logger.info("Activating.")
        self._main_window.present()

    def do_shutdown(self):
        self._logger.info("Shutting down.")
        self._main_view_model.shutdown()
        self._orchestrator.shutdown()
        self._agent.shutdown()
        self._mcp.shutdown()
        self._markdown.shutdown()
        self._configuration.shutdown()
        Adw.Application.do_shutdown(self)

    def _create_action(self, name, callback, shortcuts=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)
