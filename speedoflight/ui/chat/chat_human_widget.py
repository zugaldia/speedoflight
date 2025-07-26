from speedoflight.models import (
    GBaseMessage,
    MessageRole,
    RequestMessage,
    TextBlockRequest,
)
from speedoflight.ui.chat.chat_base_widget import ChatBaseWidget


class ChatHumanWidget(ChatBaseWidget):
    def __init__(self, message: GBaseMessage) -> None:
        super().__init__()
        content = (
            message.data.content
            if isinstance(message.data, RequestMessage)
            and message.data.role == MessageRole.HUMAN
            else []
        )

        for block in content:
            if isinstance(block, TextBlockRequest):
                self._add_plain_text(block.text, "human-message")
            else:
                self._logger.warning(f"Unsupported human block type: {type(block)}")
