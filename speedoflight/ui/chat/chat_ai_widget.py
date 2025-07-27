from speedoflight.models import (
    GBaseMessage,
    MessageRole,
    ResponseMessage,
    TextBlockResponse,
    ToolInputResponse,
    ToolTextOutputResponse,
)
from speedoflight.ui.chat.chat_base_widget import ChatBaseWidget
from speedoflight.utils import safe_json


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
                # TODO: Improve the visualization of text blocks in the
                # context of citations (e.g. web search results)
                self._add_markdown_text(block.text)
            elif isinstance(block, ToolInputResponse):
                # TODO: Change icon based on server vs local tool
                self._add_expandable_text(
                    title=f"Tool Request: {block.name}",
                    subtitle=f"Call ID: {block.call_id}",
                    content=safe_json(block.arguments),
                    class_name="monospace-content",
                    icon_name="network-transmit",
                    expanded=False,
                )
            elif isinstance(block, ToolTextOutputResponse):
                self._add_expandable_text(
                    title=f"Tool Response: {block.name}",
                    subtitle=f"Call ID: {block.call_id}",
                    content=block.text,
                    class_name="monospace-content",
                    icon_name=self._get_icon_name("network-receive", block.is_error),
                    expanded=block.is_error,
                )
            else:
                self._logger.warning(f"Unsupported AI block type: {type(block)}")
