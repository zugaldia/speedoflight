import json

from gi.repository import Adw, Gtk, Pango  # type: ignore

from speedoflight.constants import DEFAULT_MARGIN, DEFAULT_SPACING
from speedoflight.models import GBaseMessage
from speedoflight.ui.chat.chat_item_mixin import ChatItemMixin


class ChatAiWidget(Gtk.Box, ChatItemMixin):
    def __init__(self, message: GBaseMessage) -> None:
        Gtk.Box.__init__(self)
        ChatItemMixin.__init__(self)

        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(0)
        self.set_margin_top(DEFAULT_MARGIN)
        self.set_margin_bottom(DEFAULT_MARGIN)
        self.set_margin_start(DEFAULT_MARGIN)
        self.set_margin_end(DEFAULT_MARGIN)

        # Set up the pieces of this widget
        self._setup_cloud_tools(message)
        self._setup_text(message)
        self._setup_tool_calls(message)

    def _setup_cloud_tools(self, message: GBaseMessage):
        if (
            hasattr(message.data, "additional_kwargs")
            and message.data.additional_kwargs
            and "tool_outputs" in message.data.additional_kwargs
        ):
            tool_outputs = message.data.additional_kwargs["tool_outputs"]
            if tool_outputs:
                for tool_output in tool_outputs:
                    tool_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                    tool_box.set_spacing(DEFAULT_SPACING)
                    tool_box.set_margin_top(DEFAULT_MARGIN)
                    tool_box.set_margin_bottom(DEFAULT_MARGIN)
                    tool_box.set_margin_start(DEFAULT_MARGIN)
                    tool_box.set_margin_end(DEFAULT_MARGIN)

                    tool_icon = Gtk.Image()
                    tool_icon.set_from_icon_name("network-transmit-receive")
                    tool_icon.set_icon_size(Gtk.IconSize.NORMAL)
                    tool_box.append(tool_icon)

                    tool_label = Gtk.Label()
                    tool_type = tool_output.get("type", "unknown_tool")
                    tool_status = tool_output.get("status", "unknown")
                    tool_label.set_text(f"{tool_type} ({tool_status})")
                    tool_label.set_xalign(0.0)
                    tool_box.append(tool_label)

                    self.append(tool_box)

    def _setup_text(self, message: GBaseMessage):
        lines = self.extract_text(message.data)
        if lines:
            text = "\n".join(lines)
            text_label = Gtk.Label()
            text_label.set_text(text)
            text_label.set_wrap(True)
            text_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            text_label.set_xalign(0.0)
            text_label.set_selectable(True)
            self.append(text_label)

    def _setup_tool_calls(self, message: GBaseMessage):
        # Create individual expander rows for each tool call
        if hasattr(message.data, "tool_calls") and message.data.tool_calls:
            total_tools = len(message.data.tool_calls)
            for i, tool_call in enumerate(message.data.tool_calls):
                tool_name = tool_call.get("name", "unnamed_tool")
                tool_call_json = json.dumps(tool_call, indent=2)

                first_line = tool_call_json if tool_call_json else "No output."
                first_line = first_line.replace("\n", "").replace("\r", "")
                if len(first_line) > 50:
                    first_line = first_line[:47] + "..."

                tool_expander = Adw.ExpanderRow()
                tool_expander.set_title(f"{tool_name} request ({i + 1}/{total_tools})")
                tool_expander.set_subtitle(first_line)

                tool_icon = Gtk.Image()
                tool_icon.set_from_icon_name("network-transmit")
                tool_icon.set_icon_size(Gtk.IconSize.NORMAL)
                tool_expander.add_prefix(tool_icon)

                tool_call_label = Gtk.Label()
                tool_call_label.set_text(tool_call_json)
                tool_call_label.set_wrap(True)
                tool_call_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
                tool_call_label.set_xalign(0.0)
                tool_call_label.set_selectable(True)
                tool_call_label.get_style_context().add_class("monospace-content")
                tool_call_label.set_margin_top(DEFAULT_MARGIN)
                tool_call_label.set_margin_bottom(DEFAULT_MARGIN)
                tool_call_label.set_margin_start(DEFAULT_MARGIN)
                tool_call_label.set_margin_end(DEFAULT_MARGIN)

                tool_expander.add_row(tool_call_label)
                self.append(tool_expander)
