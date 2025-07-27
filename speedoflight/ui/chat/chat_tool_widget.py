from speedoflight.models import (
    GBaseMessage,
    MessageRole,
    RequestMessage,
    ToolImageOutputRequest,
    ToolTextOutputRequest,
)
from speedoflight.ui.chat.chat_base_widget import ChatBaseWidget


class ChatToolWidget(ChatBaseWidget):
    def __init__(self, message: GBaseMessage) -> None:
        super().__init__()
        content = (
            message.data.content
            if isinstance(message.data, RequestMessage)
            and message.data.role == MessageRole.TOOL
            else []
        )

        for block in content:
            if isinstance(block, ToolTextOutputRequest):
                self._add_expandable_text(
                    title=f"Tool Response: {block.name}",
                    subtitle=f"Call ID: {block.call_id}",
                    content=block.text,
                    class_name="monospace-content",
                    icon_name=self._get_icon_name("network-receive", block.is_error),
                    expanded=block.is_error,
                )
            elif isinstance(block, ToolImageOutputRequest):
                self._add_expandable_image(
                    title=f"Tool Response: {block.name}",
                    subtitle=f"Call ID: {block.call_id}",
                    data=block.data,
                    mime_type=block.mime_type.value,
                    class_name="monospace-content",
                    icon_name=self._get_icon_name(
                        "image-x-generic-symbolic",
                        block.is_error,
                    ),
                    expanded=True,
                )
            else:
                self._logger.warning(f"Unsupported tool block type: {type(block)}")
