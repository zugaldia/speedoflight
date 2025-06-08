from gi.repository import Gdk, GObject, Gtk  # type: ignore

from speedoflight.constants import DEFAULT_MARGIN, DEFAULT_SPACING, SEND_MESSAGE_SIGNAL
from speedoflight.utils import is_empty


class InputWidget(Gtk.Box):
    __gsignals__ = {SEND_MESSAGE_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,))}

    def __init__(self) -> None:
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=DEFAULT_SPACING
        )
        self.set_margin_top(DEFAULT_MARGIN)
        self.set_margin_bottom(DEFAULT_MARGIN)
        self.set_margin_start(DEFAULT_MARGIN)
        self.set_margin_end(DEFAULT_MARGIN)

        self.text_view = Gtk.TextView()
        self.text_view.set_hexpand(True)
        self.text_view.set_size_request(-1, 50)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_top_margin(DEFAULT_MARGIN)
        self.text_view.set_bottom_margin(DEFAULT_MARGIN)
        self.text_view.set_left_margin(DEFAULT_MARGIN)
        self.text_view.set_right_margin(DEFAULT_MARGIN)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.text_view.add_controller(key_controller)

        self.append(self.text_view)

        self.send_button = Gtk.Button(label="Send")
        self.send_button.connect("clicked", self._on_send_clicked)
        self.append(self.send_button)

        # Start disabled by default (until the agent is ready)
        self.set_enabled(False)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Return:
            if state & Gdk.ModifierType.SHIFT_MASK:
                return False
            else:
                self._send_message()
                return True
        return False

    def _on_send_clicked(self, button):
        self._send_message()

    def _send_message(self):
        buffer = self.text_view.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        if not is_empty(text):
            self.emit(SEND_MESSAGE_SIGNAL, text.strip())
            buffer.set_text("")

    def set_enabled(self, enabled: bool):
        self.text_view.set_sensitive(enabled)
        self.send_button.set_sensitive(enabled)
        if enabled:
            self.text_view.grab_focus()
