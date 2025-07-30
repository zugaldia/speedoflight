import logging

from gi.repository import Gio, GLib, Gtk  # type: ignore

from speedoflight.models import GBaseMessage, MessageRole
from speedoflight.ui.chat.chat_ai_widget import ChatAiWidget
from speedoflight.ui.chat.chat_human_widget import ChatHumanWidget
from speedoflight.ui.chat.chat_sol_widget import ChatSolWidget
from speedoflight.ui.chat.chat_tool_widget import ChatToolWidget


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

    def _on_items_changed(
        self, store: Gio.ListStore, position: int, removed: int, added: int
    ):
        if added > 0:
            GLib.idle_add(self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        item_count = self.store.get_n_items()
        if item_count > 0:
            self.scroll_to(item_count - 1, Gtk.ListScrollFlags.FOCUS)
        return False

    def _on_factory_setup(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        list_item.set_child(Gtk.Label(label="Loading..."))

    def _on_factory_bind(
        self, factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        message = list_item.get_item()
        if message is None or not isinstance(message, GBaseMessage):
            self._logger.warning("List item has no valid message data.")
            return

        # The message widget
        message_widget = None
        if message.data.role == MessageRole.SOL:
            message_widget = ChatSolWidget(message)
        elif message.data.role == MessageRole.HUMAN:
            message_widget = ChatHumanWidget(message)
        elif message.data.role == MessageRole.AI:
            message_widget = ChatAiWidget(message)
        elif message.data.role == MessageRole.TOOL:
            message_widget = ChatToolWidget(message)
        else:
            self._logger.warning(f"Unable to render message ({message.data.role}).")
            return

        # Wrap it in a revealer
        revealer = Gtk.Revealer()
        revealer.set_reveal_child(False)
        revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        revealer.set_transition_duration(500)
        revealer.set_child(message_widget)
        list_item.set_child(revealer)
        GLib.idle_add(revealer.set_reveal_child, True)

    def add_message(self, message: GBaseMessage):
        self.store.append(message)

    def clear_messages(self):
        self.store.remove_all()
