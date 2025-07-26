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
                icon_name = (
                    "dialog-error-symbolic" if block.is_error else "network-receive"
                )
                self._add_expandable_text(
                    title=f"Tool Response: {block.name}",
                    subtitle=f"Call ID: {block.call_id}",
                    content=block.text,
                    class_name="monospace-content",
                    icon_name=icon_name,
                    expanded=block.is_error,
                )
            elif isinstance(block, ToolImageOutputRequest):
                icon_name = (
                    "dialog-error-symbolic"
                    if block.is_error
                    else "image-x-generic-symbolic"
                )
                self._add_expandable_image(
                    title=f"Tool Response: {block.name}",
                    subtitle=f"Call ID: {block.call_id}",
                    data=block.data,
                    mime_type=block.mime_type.value,
                    class_name="monospace-content",
                    icon_name=icon_name,
                    expanded=True,
                )
            else:
                self._logger.warning(f"Unsupported tool block type: {type(block)}")
