from gi.repository import Gtk, Pango  # type: ignore

from speedoflight.constants import DEFAULT_MARGIN
from speedoflight.models import GBaseMessage
from speedoflight.ui.chat.chat_item_mixin import ChatItemMixin


class HumanMessageWidget(Gtk.Label, ChatItemMixin):
    def __init__(self, message: GBaseMessage) -> None:
        super().__init__()

        self.set_wrap(True)
        self.set_xalign(0.0)
        self.set_selectable(True)
        self.set_margin_top(DEFAULT_MARGIN)
        self.set_margin_bottom(DEFAULT_MARGIN)
        self.set_margin_start(DEFAULT_MARGIN)
        self.set_margin_end(DEFAULT_MARGIN)

        # Add CSS class for styling
        self.get_style_context().add_class("human-message")

        lines = self.extract_text(message.data)
        text = "\n".join(lines)
        self.set_text(text)
        self.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
