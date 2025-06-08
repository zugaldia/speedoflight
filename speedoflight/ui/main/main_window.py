import logging
import random

from gi.repository import Adw, Gdk, Gtk  # type: ignore
from langchain_core.messages import HumanMessage

from speedoflight.constants import (
    AGENT_MESSAGE_SIGNAL,
    AGENT_READY_SIGNAL,
    AGENT_RUN_COMPLETED_SIGNAL,
    AGENT_RUN_STARTED_SIGNAL,
    APPLICATION_NAME,
)
from speedoflight.models import GBaseMessage
from speedoflight.services.orchestrator.orchestrator_service import OrchestratorService
from speedoflight.ui.main.chat_widget import ChatWidget
from speedoflight.ui.main.input_widget import InputWidget
from speedoflight.ui.main.status_widget import StatusWidget


class MainWindow(Adw.ApplicationWindow):
    _processing_messages = [
        "Agenting...",
        "Analyzing...",
        "Brewing...",
        "Computing...",
        "Conjuring...",
        "Contemplating...",
        "Pondering...",
        "Reasoning...",
        "Thinking...",
        "Vibing...",
    ]

    def __init__(
        self, application: Adw.Application, orchestrator: OrchestratorService
    ) -> None:
        super().__init__(application=application)
        self._logger = logging.getLogger(__name__)
        self.set_title(APPLICATION_NAME)
        self.set_default_size(800, 600)
        self._load_css()

        self._orchestrator = orchestrator
        self._orchestrator.connect(AGENT_MESSAGE_SIGNAL, self._on_agent_message)
        self._orchestrator.connect(AGENT_READY_SIGNAL, self._on_agent_ready)
        self._orchestrator.connect(AGENT_RUN_STARTED_SIGNAL, self._on_agent_run_started)
        self._orchestrator.connect(
            AGENT_RUN_COMPLETED_SIGNAL, self._on_agent_run_completed
        )

        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        header_bar = Adw.HeaderBar()
        header_bar.set_title_widget(Gtk.Label(label=APPLICATION_NAME))
        toolbar_view.add_top_bar(header_bar)

        self._chat_widget = ChatWidget()

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_child(self._chat_widget)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_hexpand(True)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar_view.set_content(scrolled_window)

        bottom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.input_widget = InputWidget()
        self.input_widget.connect("send-message", self._on_send_message)
        bottom_box.append(self.input_widget)

        self.status_widget = StatusWidget()
        bottom_box.append(self.status_widget)

        toolbar_view.add_bottom_bar(bottom_box)

    def _load_css(self):
        default_display = Gdk.Display.get_default()
        if default_display:
            css_provider = Gtk.CssProvider()
            css_provider.load_from_path("speedoflight/data/style.css")
            Gtk.StyleContext().add_provider_for_display(
                default_display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _on_send_message(self, widget, text):
        message = GBaseMessage(data=HumanMessage(content=text))
        self._chat_widget.add_message(message)
        self.status_widget.set_status("Starting agent...")
        self._orchestrator.run_agent(text)

    def _on_agent_message(self, orchestrator, message: GBaseMessage):
        self._chat_widget.add_message(message)

    def _on_agent_ready(self, orchestrator):
        self.status_widget.set_status(
            "Ready. (Enter to submit, Shift+Enter for a new line.)"
        )
        self.status_widget.set_activity_mode(False)
        self.input_widget.set_enabled(True)

    def _on_agent_run_started(self, orchestrator):
        message = random.choice(self._processing_messages)
        self.status_widget.set_status(message)
        self.status_widget.set_activity_mode(True)
        self.input_widget.set_enabled(False)

    def _on_agent_run_completed(self, orchestrator):
        self.status_widget.set_status("Done.")
        self.status_widget.set_activity_mode(False)
        self.input_widget.set_enabled(True)
