from speedoflight.constants import TOOL_COMPUTER_USE_NAME
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
            # TODO: We should use a GTK source view as well because this is
            # JSON after all, and it would be good to have it with color syntax.
            if isinstance(block, ToolTextOutputRequest):
                self._add_expandable_text(
                    title=f"Tool Response: {block.name}",
                    subtitle=f"Call ID: {block.call_id}",
                    content=block.text,
                    class_name="monospace",
                    icon_name="network-receive",
                    expanded=block.is_error,
                    is_error=block.is_error,
                )
            elif isinstance(block, ToolImageOutputRequest):
                expanded = not (block.name == TOOL_COMPUTER_USE_NAME)
                self._add_expandable_image(
                    title=f"Tool Response: {block.name}",
                    subtitle=f"Call ID: {block.call_id}",
                    data=block.data,
                    mime_type=block.mime_type.value,
                    class_name="monospace",
                    icon_name="image-x-generic-symbolic",
                    expanded=expanded,
                )
            else:
                self._logger.warning(f"Unsupported tool block type: {type(block)}")
