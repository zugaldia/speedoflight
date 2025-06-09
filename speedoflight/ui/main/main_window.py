import logging

from gi.repository import Adw, Gdk, GObject, Gtk  # type: ignore
from langchain_core.messages import HumanMessage

from speedoflight.constants import AGENT_MESSAGE_SIGNAL, APPLICATION_NAME
from speedoflight.models import GBaseMessage
from speedoflight.ui.main.chat_widget import ChatWidget
from speedoflight.ui.main.input_widget import InputWidget
from speedoflight.ui.main.main_view_model import MainViewModel
from speedoflight.ui.main.main_view_state import MainViewState
from speedoflight.ui.main.status_widget import StatusWidget


class MainWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        application: Adw.Application,
        view_model: MainViewModel,
    ) -> None:
        super().__init__(application=application)
        self._logger = logging.getLogger(__name__)
        self.set_title(APPLICATION_NAME)
        self.set_default_size(800, 600)
        self._load_css()

        self._view_model = view_model
        self._view_model.connect(AGENT_MESSAGE_SIGNAL, self._on_agent_message)
        self._view_model.view_state.connect(
            "notify::status-text", self._on_status_text_changed
        )
        self._view_model.view_state.connect(
            "notify::agent-state", self._on_agent_state_changed
        )
        self._view_model.view_state.connect(
            "notify::input-enabled", self._on_input_enabled_changed
        )
        self._view_model.view_state.connect(
            "notify::activity-mode", self._on_activity_mode_changed
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
        self._view_model.run_agent(text)

    def _on_agent_message(self, view_model, message: GBaseMessage):
        self._chat_widget.add_message(message)

    def _on_status_text_changed(
        self,
        view_state: MainViewState,
        param_spec: GObject.ParamSpec,
    ):
        self.status_widget.set_status(view_state.status_text)

    def _on_agent_state_changed(
        self,
        view_state: MainViewState,
        param_spec: GObject.ParamSpec,
    ):
        self._logger.info(f"Agent state changed to: {view_state.agent_state}")

    def _on_input_enabled_changed(
        self,
        view_state: MainViewState,
        param_spec: GObject.ParamSpec,
    ):
        self.input_widget.set_enabled(view_state.input_enabled)

    def _on_activity_mode_changed(
        self,
        view_state: MainViewState,
        param_spec: GObject.ParamSpec,
    ):
        self.status_widget.set_activity_mode(view_state.activity_mode)
