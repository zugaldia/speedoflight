import logging

from gi.repository import GObject, Gtk  # type: ignore

from speedoflight.constants import DEFAULT_MARGIN, DEFAULT_SPACING, SEND_MESSAGE_SIGNAL
from speedoflight.utils import is_empty


class InputWidget(Gtk.Box):
    __gsignals__ = {SEND_MESSAGE_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,))}

    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=DEFAULT_SPACING
        )
        self._logger = logging.getLogger(__name__)
        self.set_margin_top(DEFAULT_MARGIN)
        self.set_margin_bottom(DEFAULT_MARGIN)
        self.set_margin_start(DEFAULT_MARGIN)
        self.set_margin_end(DEFAULT_MARGIN)

        self._entry = Gtk.Entry()
        self._entry.set_hexpand(True)
        self._entry.set_placeholder_text("Type your message here.")
        self._entry.connect("activate", self._on_activated)  # Pressing Enter
        self._setup_autocompletion()
        self._setup_icons()
        self.append(self._entry)

        self._send_button = Gtk.Button(label="Send")
        self._send_button.connect("clicked", self._on_send_clicked)
        self._send_button.get_style_context().add_class("suggested-action")
        self.append(self._send_button)

        # Start disabled by default (until the agent is ready)
        self.set_enabled(False)

    def _setup_autocompletion(self):
        list_store = Gtk.ListStore(str)
        slash_commands = ["/help", "/clear"]
        for command in slash_commands:
            list_store.append([command])

        completion = Gtk.EntryCompletion()
        completion.set_model(list_store)
        completion.set_text_column(0)
        completion.set_minimum_key_length(1)
        completion.set_popup_completion(True)
        self._entry.set_completion(completion)

    def _setup_icons(self):
        self._entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, "edit-clear-symbolic"
        )

        self._entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        self._entry.connect("icon-press", self._on_icon_press)

    def _on_icon_press(self, entry, icon_pos):
        if icon_pos == Gtk.EntryIconPosition.PRIMARY:
            # TODO: Enable adding attachments?
            self._logger.info("Primary icon pressed.")
        elif icon_pos == Gtk.EntryIconPosition.SECONDARY:
            self._entry.set_text("")

    def _on_activated(self, entry):
        self._send_message()

    def _on_send_clicked(self, button):
        self._send_message()

    def _send_message(self):
        # Workaround for the warning below
        if not self._send_button.is_sensitive():
            self._logger.warning("Send button is not sensitive, ignoring send request.")
            return
        buffer: Gtk.EntryBuffer = self._entry.get_buffer()
        text = buffer.get_text()
        if not is_empty(text):
            self.emit(SEND_MESSAGE_SIGNAL, text.strip())
            self._entry.set_text("")

    def set_enabled(self, enabled: bool):
        # FIXME: Allowing this line will generate a GTK warning I don't understand:
        # Gtk-WARNING **: 08:49:47.154: GtkText - did not receive a focus-out event.
        # If you handle this event, you must return GDK_EVENT_PROPAGATE so the
        # default handler gets the event as well
        # self._entry.set_sensitive(enabled)
        self._send_button.set_sensitive(enabled)
        if enabled:
            self._entry.grab_focus()

    def pulse_entry(self) -> bool:
        # TODO: Doesn't seem to do anything?
        self._entry.progress_pulse()
        return True

    def set_fraction(self, fraction: float) -> None:
        self._entry.set_progress_fraction(fraction)
