from gi.repository import Adw, Gtk, Pango  # type: ignore

from speedoflight.constants import DEFAULT_MARGIN
from speedoflight.models import GBaseMessage
from speedoflight.ui.chat.chat_item_mixin import ChatItemMixin
from speedoflight.utils import base64_to_pixbuf


class ChatToolWidget(Adw.ExpanderRow, ChatItemMixin):
    def __init__(self, message: GBaseMessage) -> None:
        Adw.ExpanderRow.__init__(self)
        ChatItemMixin.__init__(self)

        self.set_margin_top(DEFAULT_MARGIN)
        self.set_margin_bottom(DEFAULT_MARGIN)
        self.set_margin_start(DEFAULT_MARGIN)
        self.set_margin_end(DEFAULT_MARGIN)

        lines = self.extract_text(message.data)
        text = "\n".join(lines)

        # Create title and summary for collapsed state
        tool_name = getattr(message.data, "name", "unnamed tool")
        subtitle = text if text else "No text output"
        subtitle = text[:50] + "..." if len(text) > 50 else text
        self.set_title(f"{tool_name} response")
        self.set_subtitle(subtitle)

        # Add tool icon prefix
        tool_icon = Gtk.Image()
        tool_icon.set_from_icon_name("network-receive")
        tool_icon.set_icon_size(Gtk.IconSize.NORMAL)
        self.add_prefix(tool_icon)

        if text:
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

        # Handle image artifacts
        artifacts = self.extract_artifacts(message.data)
        has_images = False
        for artifact in artifacts:
            data = artifact.get("data")
            mime_type = artifact.get("mimeType")
            if data and mime_type:
                pixbuf = base64_to_pixbuf(data, mime_type)
                if pixbuf:
                    picture = Gtk.Picture()
                    picture.set_pixbuf(pixbuf)
                    picture.set_content_fit(Gtk.ContentFit.SCALE_DOWN)
                    picture.set_can_shrink(True)
                    picture.set_size_request(pixbuf.get_width(), pixbuf.get_height())
                    picture.set_margin_top(DEFAULT_MARGIN)
                    picture.set_margin_bottom(DEFAULT_MARGIN)
                    picture.set_margin_start(DEFAULT_MARGIN)
                    picture.set_margin_end(DEFAULT_MARGIN)
                    self.add_row(picture)
                    has_images = True

        # Auto-expand if there are image artifacts
        if has_images:
            self.set_expanded(True)
