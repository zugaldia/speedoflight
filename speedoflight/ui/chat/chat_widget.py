import logging
from typing import Union

from gi.repository import Gio, GLib, Gtk  # type: ignore

from speedoflight.constants import DEFAULT_MARGIN
from speedoflight.models import GBaseMessage, MessageRole
from speedoflight.ui.chat.chat_ai_item import AIMessageWidget
from speedoflight.ui.chat.chat_human_item import HumanMessageWidget
from speedoflight.ui.chat.chat_tool_item import ToolMessageWidget


class ChatWidget(Gtk.ListView):
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)
        self.store = Gio.ListStore(item_type=GBaseMessage)
        self.store.connect("items-changed", self._on_items_changed)

        selection_model = Gtk.NoSelection(model=self.store)
        super().__init__(model=selection_model)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)
        self.set_factory(factory)

    def _on_items_changed(self, store, position, removed, added):
        if added > 0:
            GLib.idle_add(self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        item_count = self.store.get_n_items()
        if item_count > 0:
            self.scroll_to(item_count - 1, Gtk.ListScrollFlags.FOCUS)
        return False

    def _on_factory_setup(self, factory, list_item) -> None:
        label = Gtk.Label(label="Loading...")
        label.set_wrap(True)
        label.set_xalign(0.0)
        label.set_selectable(True)
        label.set_margin_top(DEFAULT_MARGIN)
        label.set_margin_bottom(DEFAULT_MARGIN)
        label.set_margin_start(DEFAULT_MARGIN)
        label.set_margin_end(DEFAULT_MARGIN)
        list_item.set_child(label)

    def _on_factory_bind(self, factory, list_item) -> None:
        message: GBaseMessage = list_item.get_item()
        widget: Union[HumanMessageWidget, AIMessageWidget, ToolMessageWidget, Gtk.Label]
        if message.data.type == MessageRole.HUMAN.value:
            widget = HumanMessageWidget(message)
        elif message.data.type == MessageRole.AI.value:
            widget = AIMessageWidget(message)
        elif message.data.type == MessageRole.TOOL.value:
            widget = ToolMessageWidget(message)
        else:
            widget = Gtk.Label(label=f"Unable to render message({message.data.type}).")
        list_item.set_child(widget)

    def add_message(self, message: GBaseMessage):
        self.store.append(message)
