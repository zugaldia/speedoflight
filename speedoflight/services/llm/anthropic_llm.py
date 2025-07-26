from typing import Iterable

from anthropic import AsyncAnthropic
from anthropic.types import (
    Base64ImageSourceParam,
    ImageBlockParam,
    Message,
    MessageParam,
    TextBlockParam,
    ToolChoiceAutoParam,
    ToolParam,
    ToolResultBlockParam,
    ToolUseBlockParam,
)
from mcp import types

from speedoflight.models import (
    AnthropicConfig,
    BaseMessage,
    MessageRole,
    RequestMessage,
    ResponseMessage,
    StopReason,
    TextBlockRequest,
    TextBlockResponse,
    ToolImageOutputRequest,
    ToolInputResponse,
    ToolTextOutputRequest,
    Usage,
)
from speedoflight.services.llm.base_llm import BaseLlmService
from speedoflight.utils import is_empty


class AnthropicLlm(BaseLlmService):
    def __init__(self, config: AnthropicConfig):
        super().__init__(service_name="anthropic")
        self._config = config
        if is_empty(config.api_key):
            raise ValueError("An API key must be provided.")
        self._logger.info(f"Using Anthropic config: {config}")
        self._client = AsyncAnthropic(api_key=config.api_key)

    async def generate_message(
        self,
        app_messages: list[BaseMessage],
        mcp_tools: dict[str, list[types.Tool]],
    ) -> ResponseMessage:
        messages: Iterable[MessageParam] = [self.to_native(msg) for msg in app_messages]
        tools: Iterable[ToolParam] = [
            ToolParam(
                input_schema=tool.inputSchema,
                name=tool.name,
                description=tool.description
                or f"This is the {tool.name} tool by the {server_name} MCP server.",
            )
            for server_name, tools_list in mcp_tools.items()
            for tool in tools_list
        ]

        result: Message = await self._client.messages.create(
            max_tokens=self._config.max_tokens,
            temperature=self._config.temperature,
            messages=messages,
            model=self._config.model,
            tools=tools,
            tool_choice=ToolChoiceAutoParam(
                type="auto", disable_parallel_tool_use=True
            ),
        )

        # self._logger.info(f"Generated message: {result}")
        return self.from_native(result)

    def to_native(self, app_msg: BaseMessage) -> MessageParam:
        if app_msg.role == MessageRole.HUMAN:
            role = "user"
        elif app_msg.role == MessageRole.AI:
            role = "assistant"
        elif app_msg.role == MessageRole.TOOL:
            role = "user"  # Anthropic treats tool responses as user messages
        else:
            raise ValueError(f"Unsupported message role: {app_msg.role}")

        content = []
        message_content = (
            app_msg.content
            if isinstance(app_msg, (RequestMessage, ResponseMessage))
            else []
        )

        for block in message_content:
            if isinstance(block, (TextBlockRequest, TextBlockResponse)):
                content.append(TextBlockParam(type="text", text=block.text))
            elif isinstance(block, ToolInputResponse):
                content.append(
                    ToolUseBlockParam(
                        type="tool_use",
                        id=block.call_id,
                        name=block.name,
                        input=block.arguments,
                    )
                )
            elif isinstance(block, ToolTextOutputRequest):
                content.append(
                    ToolResultBlockParam(
                        type="tool_result",
                        tool_use_id=block.call_id,
                        is_error=block.is_error,
                        content=[TextBlockParam(type="text", text=block.text)],
                    )
                )
            elif isinstance(block, ToolImageOutputRequest):
                content.append(
                    ToolResultBlockParam(
                        type="tool_result",
                        tool_use_id=block.call_id,
                        is_error=block.is_error,
                        content=[
                            ImageBlockParam(
                                type="image",
                                source=Base64ImageSourceParam(
                                    type="base64",
                                    data=block.data,
                                    media_type=block.mime_type.value,
                                ),
                            )
                        ],
                    )
                )
            else:
                self._logger.warning(f"Unsupported content block type: {type(block)}")

        return MessageParam(
            role=role,
            content=content,
        )

    def from_native(self, native_msg: Message) -> ResponseMessage:
        content = []
        for block in native_msg.content:
            if block.type == "text":
                content.append(TextBlockResponse(text=block.text))
            elif block.type == "tool_use":
                tool_input = block.input if isinstance(block.input, dict) else {}
                content.append(
                    ToolInputResponse(
                        call_id=block.id,
                        name=block.name,
                        arguments=tool_input,
                    )
                )
            else:
                self._logger.warning(f"Unsupported content block type: {block.type}")

        if native_msg.role == "assistant":
            role = MessageRole.AI
        else:
            raise ValueError(f"Unsupported message role: {native_msg.role}")

        stop_reason = StopReason.END_TURN
        if native_msg.stop_reason == "end_turn":
            stop_reason = StopReason.END_TURN
        elif native_msg.stop_reason == "max_tokens":
            stop_reason = StopReason.MAX_TOKENS
        elif native_msg.stop_reason == "stop_sequence":
            stop_reason = StopReason.STOP_SEQUENCE
        elif native_msg.stop_reason == "tool_use":
            stop_reason = StopReason.TOOL_USE
        elif native_msg.stop_reason == "pause_turn":
            stop_reason = StopReason.PAUSE_TURN
        elif native_msg.stop_reason == "refusal":
            stop_reason = StopReason.REFUSAL
        else:
            self._logger.warning(f"Unsupported stop reason: {native_msg.stop_reason}")

        usage = Usage(
            input_tokens=native_msg.usage.input_tokens,
            output_tokens=native_msg.usage.output_tokens,
        )

        return ResponseMessage(
            role=role,
            content=content,
            provider=self.service_name,
            model=native_msg.model,
            usage=usage,
            stop_reason=stop_reason,
        )
