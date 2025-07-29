from typing import Iterable

from anthropic import AsyncAnthropic
from anthropic.types import (
    Base64ImageSourceParam,
    ImageBlockParam,
    Message,
    MessageParam,
    ServerToolUseBlock,
    TextBlock,
    TextBlockParam,
    ToolChoiceAutoParam,
    ToolParam,
    ToolResultBlockParam,
    ToolUseBlock,
    WebSearchTool20250305Param,
    WebSearchToolResultBlock,
    WebSearchToolResultError,
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
    ToolEnvironment,
    ToolImageOutputRequest,
    ToolInputResponse,
    ToolTextOutputRequest,
    ToolTextOutputResponse,
    Usage,
)
from speedoflight.services.llm.base_llm import BaseLlmService
from speedoflight.utils import is_empty, safe_json

TOOL_WEB_SEARCH_NAME = "web_search"


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
        tools: list[types.Tool],
    ) -> ResponseMessage:
        messages: Iterable[MessageParam] = [self.to_native(msg) for msg in app_messages]
        native_tools: Iterable[ToolParam] = [
            ToolParam(
                name=tool.name,
                description=tool.description or f"This is the {tool.name} tool.",
                input_schema=tool.inputSchema,
            )
            for tool in tools
        ]

        cloud_tools = []
        if self._config.enable_web_search:
            # TODO: Support additional parameters for web search
            # https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-search-tool#tool-definition
            cloud_tools.append(
                WebSearchTool20250305Param(
                    name=TOOL_WEB_SEARCH_NAME, type="web_search_20250305"
                )
            )

        result: Message = await self._client.messages.create(
            max_tokens=self._config.max_tokens,
            system=self._get_system_prompt(),
            temperature=self._config.temperature,
            messages=messages,
            model=self._config.model,
            tools=native_tools + cloud_tools,
            tool_choice=ToolChoiceAutoParam(
                type="auto", disable_parallel_tool_use=True
            ),
        )

        return self.from_native(result)

    def to_native(self, app_msg: BaseMessage) -> MessageParam:
        if isinstance(app_msg, ResponseMessage) and app_msg.raw is not None:
            return MessageParam(
                role=app_msg.raw.role,
                content=app_msg.raw.content,
            )

        if app_msg.role in [MessageRole.HUMAN, MessageRole.TOOL]:
            role = "user"  # Anthropic treats tool responses as user messages
        else:
            raise ValueError(f"Unsupported message role: {app_msg.role}")

        content = []
        req_content = app_msg.content if isinstance(app_msg, RequestMessage) else []
        for block in req_content:
            if isinstance(block, TextBlockRequest):
                content.append(TextBlockParam(type="text", text=block.text))
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
                self._logger.warning(
                    f"Unsupported app content block type: {type(block)}"
                )

        if len(content) == 0:
            self._logger.warning(
                f"No supported native content in application message: {app_msg}"
            )

        return MessageParam(
            role=role,
            content=content,
        )

    def from_native(self, native_msg: Message) -> ResponseMessage:
        if native_msg.role == "assistant":
            role = MessageRole.AI
        else:
            raise ValueError(f"Unsupported native message role: {native_msg.role}")

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
            self._logger.warning(
                f"Unsupported native stop reason: {native_msg.stop_reason}"
            )

        usage = Usage(
            input_tokens=native_msg.usage.input_tokens,
            output_tokens=native_msg.usage.output_tokens,
        )

        content = []
        for block in native_msg.content:
            if isinstance(block, TextBlock):
                # TODO: When citations are present, Anthropic splits the text
                # response into multiple text blocks, some of them with citations
                # content. This is making the rendering right now a bit strange.
                content.append(TextBlockResponse(text=block.text))
            elif isinstance(block, ToolUseBlock):
                content.append(
                    ToolInputResponse(
                        call_id=block.id,
                        environment=ToolEnvironment.LOCAL,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )
            elif isinstance(block, ServerToolUseBlock):
                content.append(
                    ToolInputResponse(
                        call_id=block.id,
                        environment=ToolEnvironment.SERVER,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )
            elif isinstance(block, WebSearchToolResultBlock):
                # TODO: Maybe rename to a dedicated ToolWebSearchOutputResponse?
                if isinstance(block.content, WebSearchToolResultError):
                    content.append(
                        ToolTextOutputResponse(
                            call_id=block.tool_use_id,
                            name=TOOL_WEB_SEARCH_NAME,
                            text=block.content.error_code,
                            is_error=True,
                        )
                    )
                else:
                    content.append(
                        ToolTextOutputResponse(
                            call_id=block.tool_use_id,
                            name=TOOL_WEB_SEARCH_NAME,
                            text=safe_json(block.content),
                            is_error=False,
                        )
                    )
            else:
                self._logger.warning(
                    f"Unsupported native content block type: {type(block)}"
                )

        return ResponseMessage(
            raw=native_msg,
            role=role,
            content=content,
            provider=self.service_name,
            model=native_msg.model,
            usage=usage,
            stop_reason=stop_reason,
        )
