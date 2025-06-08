from gi.repository import Adw, Gtk, Pango  # type: ignore

from speedoflight.constants import DEFAULT_MARGIN
from speedoflight.models import GBaseMessage
from speedoflight.ui.main.chat_item_mixin import ChatItemMixin


class ToolMessageWidget(Adw.ExpanderRow, ChatItemMixin):
    def __init__(self, message: GBaseMessage) -> None:
        super().__init__()

        self.set_margin_top(DEFAULT_MARGIN)
        self.set_margin_bottom(DEFAULT_MARGIN)
        self.set_margin_start(DEFAULT_MARGIN)
        self.set_margin_end(DEFAULT_MARGIN)

        lines = self.extract_text(message.data)
        text = "\n".join(lines)

        # Create summary for collapsed state
        tool_name = getattr(message.data, "name", "Tool")
        first_line = lines[0] if lines else "No output"
        first_line = first_line.replace("\n", " ").replace("\r", " ")
        if len(first_line) > 50:
            first_line = first_line[:47] + "..."

        self.set_title(f"{tool_name} response")
        self.set_subtitle(first_line)

        # Add tool icon prefix
        tool_icon = Gtk.Image()
        tool_icon.set_from_icon_name("network-receive")
        tool_icon.set_icon_size(Gtk.IconSize.NORMAL)
        self.add_prefix(tool_icon)

        # Create label for expanded content
        content_label = Gtk.Label()
        content_label.set_text(text)
        content_label.set_wrap(True)
        content_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        content_label.set_xalign(0.0)
        content_label.set_selectable(True)
        content_label.get_style_context().add_class("monospace-content")
        content_label.set_margin_top(DEFAULT_MARGIN)
        content_label.set_margin_bottom(DEFAULT_MARGIN)
        content_label.set_margin_start(DEFAULT_MARGIN)
        content_label.set_margin_end(DEFAULT_MARGIN)

        self.add_row(content_label)
