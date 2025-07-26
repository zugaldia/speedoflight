import json

from speedoflight.models import (
    GBaseMessage,
    MessageRole,
    ResponseMessage,
    TextBlockResponse,
    ToolInputResponse,
)
from speedoflight.ui.chat.chat_base_widget import ChatBaseWidget


class ChatAiWidget(ChatBaseWidget):
    def __init__(self, message: GBaseMessage) -> None:
        super().__init__()
        content = (
            message.data.content
            if isinstance(message.data, ResponseMessage)
            and message.data.role == MessageRole.AI
            else []
        )

        for block in content:
            if isinstance(block, TextBlockResponse):
                self._add_markdown_text(block.text)
            elif isinstance(block, ToolInputResponse):
                self._add_expandable_text(
                    title=f"Tool Request: {block.name}",
                    subtitle=f"Call ID: {block.call_id}",
                    content=json.dumps(block.arguments),
                    class_name="monospace-content",
                    icon_name="network-transmit",
                    expanded=False,
                )
            else:
                self._logger.warning(f"Unsupported AI block type: {type(block)}")
