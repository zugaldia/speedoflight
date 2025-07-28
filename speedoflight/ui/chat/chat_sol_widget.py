from speedoflight.models import GBaseMessage, SolMessage
from speedoflight.ui.chat.chat_base_widget import ChatBaseWidget


class ChatSolWidget(ChatBaseWidget):
    def __init__(self, message: GBaseMessage) -> None:
        super().__init__()
        sol_message: SolMessage | None = (
            message.data if isinstance(message.data, SolMessage) else None
        )

        if sol_message:
            self._add_expandable_text(
                title="Application error",
                subtitle=sol_message.id,
                content=sol_message.message,
                class_name="monospace-content",
                icon_name="dialog-error-symbolic",
                expanded=True,
            )
