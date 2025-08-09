from datetime import datetime, timezone
from typing import Iterable

import httpx
from anthropic import NOT_GIVEN, AsyncAnthropic
from anthropic._legacy_response import LegacyAPIResponse
from anthropic.types.beta import (
    BetaBase64ImageSourceParam,
    BetaImageBlockParam,
    BetaMessage,
    BetaMessageParam,
    BetaServerToolUseBlock,
    BetaTextBlock,
    BetaTextBlockParam,
    BetaThinkingBlock,
    BetaThinkingConfigEnabledParam,
    BetaToolChoiceAutoParam,
    BetaToolComputerUse20250124Param,
    BetaToolParam,
    BetaToolResultBlockParam,
    BetaToolUseBlock,
    BetaUsage,
    BetaWebSearchTool20250305Param,
    BetaWebSearchToolResultBlock,
    BetaWebSearchToolResultError,
)
from mcp import types

from speedoflight.constants import TOOL_COMPUTER_USE_NAME, TOOL_WEB_SEARCH_NAME
from speedoflight.models import (
    AnthropicConfig,
    BaseMessage,
    MessageRole,
    RequestMessage,
    ResponseMessage,
    StopReason,
    TextBlockRequest,
    TextBlockResponse,
    ThinkingBlockResponse,
    ToolEnvironment,
    ToolImageOutputRequest,
    ToolInputResponse,
    ToolTextOutputRequest,
    ToolTextOutputResponse,
    Usage,
)
from speedoflight.services.desktop import DesktopService
from speedoflight.services.llm.base_llm import BaseLlmService
from speedoflight.utils import is_empty, safe_json

# See: https://docs.anthropic.com/en/api/rate-limits#response-headers
HEADER_RETRY_AFTER = "retry-after"
HEADER_INPUT_TOKENS_LIMIT = "anthropic-ratelimit-input-tokens-limit"
HEADER_INPUT_TOKENS_REMAINING = "anthropic-ratelimit-input-tokens-remaining"
HEADER_INPUT_TOKENS_RESET = "anthropic-ratelimit-input-tokens-reset"
HEADER_OUTPUT_TOKENS_LIMIT = "anthropic-ratelimit-output-tokens-limit"
HEADER_OUTPUT_TOKENS_REMAINING = "anthropic-ratelimit-output-tokens-remaining"
HEADER_OUTPUT_TOKENS_RESET = "anthropic-ratelimit-output-tokens-reset"
HEADER_TOKENS_LIMIT = "anthropic-ratelimit-tokens-limit"
HEADER_TOKENS_REMAINING = "anthropic-ratelimit-tokens-remaining"
HEADER_TOKENS_RESET = "anthropic-ratelimit-tokens-reset"


class AnthropicLlm(BaseLlmService):
    def __init__(self, config: AnthropicConfig, desktop: DesktopService):
        super().__init__(service_name="anthropic")
        self._config = config
        self._desktop = desktop
        if is_empty(config.api_key):
            raise ValueError("An API key must be provided.")
        self._client = AsyncAnthropic(api_key=config.api_key)

    async def generate_message(
        self,
        app_messages: list[BaseMessage],
        tools: list[types.Tool],
    ) -> ResponseMessage:
        betas = NOT_GIVEN
        cloud_tools = []
        messages: Iterable[BetaMessageParam] = [
            self.to_native(msg) for msg in app_messages
        ]

        native_tools: Iterable[BetaToolParam] = [
            BetaToolParam(
                name=tool.name,
                description=tool.description or tool.name,
                input_schema=tool.inputSchema,
            )
            for tool in tools
        ]

        if self._config.enable_web_search:
            # TODO: Support additional parameters for web search
            # https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/web-search-tool#tool-definition
            cloud_tools.append(
                BetaWebSearchTool20250305Param(
                    name=TOOL_WEB_SEARCH_NAME,
                    type="web_search_20250305",
                )
            )

        if self._config.enable_computer_use:
            betas = ["computer-use-2025-01-24"]
            width, height = self._desktop.get_target_size()
            cloud_tools.append(
                BetaToolComputerUse20250124Param(
                    display_height_px=height,
                    display_width_px=width,
                    name=TOOL_COMPUTER_USE_NAME,
                    type="computer_20250124",
                )
            )

        # We ignore the temperature value because it's incompatible with
        # enabling thinking:
        # https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking#feature-compatibility
        result: LegacyAPIResponse[
            BetaMessage
        ] = await self._client.beta.messages.with_raw_response.create(
            max_tokens=self._config.max_tokens,
            system=self._get_system_prompt(
                computer_use=self._config.enable_computer_use
            ),
            thinking=BetaThinkingConfigEnabledParam(type="enabled", budget_tokens=1024),
            messages=messages,
            model=self._config.model,
            tools=native_tools + cloud_tools,
            betas=betas,
            tool_choice=BetaToolChoiceAutoParam(
                type="auto", disable_parallel_tool_use=True
            ),
        )

        message: BetaMessage = result.parse()
        self._logger.debug(f"Generated message: {message}")

        try:
            self._track_rate_limits(result.headers, message.usage)
        except Exception as e:
            self._logger.error(f"Failed to track rate limits: {e}")

        return self.from_native(message)

    # TODO: Eventually surface this information in the UI.
    def _track_rate_limits(self, headers: httpx.Headers, usage: BetaUsage) -> None:
        self._logger.info(f"Input tokens used: {usage.input_tokens}")
        self._logger.info(f"Output tokens used: {usage.output_tokens}")

        retry_after = headers.get(HEADER_RETRY_AFTER)
        if retry_after:
            self._logger.info(f"Retry after: {retry_after} seconds")

        input_tokens_limit = int(headers.get(HEADER_INPUT_TOKENS_LIMIT))
        input_tokens_remaining = int(headers.get(HEADER_INPUT_TOKENS_REMAINING))
        input_tokens_reset_str = headers.get(HEADER_INPUT_TOKENS_RESET)
        input_tokens_reset = datetime.fromisoformat(input_tokens_reset_str)
        self._log_rate_limit(
            "Input tokens",
            input_tokens_limit,
            input_tokens_remaining,
            input_tokens_reset,
        )

        output_tokens_limit = int(headers.get(HEADER_OUTPUT_TOKENS_LIMIT))
        output_tokens_remaining = int(headers.get(HEADER_OUTPUT_TOKENS_REMAINING))
        output_tokens_reset_str = headers.get(HEADER_OUTPUT_TOKENS_RESET)
        output_tokens_reset = datetime.fromisoformat(output_tokens_reset_str)
        self._log_rate_limit(
            "Output tokens",
            output_tokens_limit,
            output_tokens_remaining,
            output_tokens_reset,
        )

        tokens_limit = int(headers.get(HEADER_TOKENS_LIMIT))
        tokens_remaining = int(headers.get(HEADER_TOKENS_REMAINING))
        tokens_reset_str = headers.get(HEADER_TOKENS_RESET)
        tokens_reset = datetime.fromisoformat(tokens_reset_str)
        self._log_rate_limit(
            "Tokens",
            tokens_limit,
            tokens_remaining,
            tokens_reset,
        )

    def _log_rate_limit(
        self, section: str, limit: int, remaining: int, reset: datetime
    ) -> None:
        percentage = (remaining / limit) * 100 if limit > 0 else 0
        seconds_until_reset = (reset - datetime.now(timezone.utc)).total_seconds()
        self._logger.info(
            f"{section} limit remaining: {percentage:.2f}%, "
            f"reset in {seconds_until_reset:.2f} seconds"
        )

    def to_native(self, app_msg: BaseMessage) -> BetaMessageParam:
        if isinstance(app_msg, ResponseMessage) and app_msg.raw is not None:
            return BetaMessageParam(
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
                content.append(BetaTextBlockParam(type="text", text=block.text))
            elif isinstance(block, ToolTextOutputRequest):
                content.append(
                    BetaToolResultBlockParam(
                        type="tool_result",
                        tool_use_id=block.call_id,
                        is_error=block.is_error,
                        content=[BetaTextBlockParam(type="text", text=block.text)],
                    )
                )
            elif isinstance(block, ToolImageOutputRequest):
                content.append(
                    BetaToolResultBlockParam(
                        type="tool_result",
                        tool_use_id=block.call_id,
                        is_error=block.is_error,
                        content=[
                            BetaImageBlockParam(
                                type="image",
                                source=BetaBase64ImageSourceParam(
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

        return BetaMessageParam(
            role=role,
            content=content,
        )

    def from_native(self, native_msg: BetaMessage) -> ResponseMessage:
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
            if isinstance(block, BetaThinkingBlock):
                content.append(ThinkingBlockResponse(text=block.thinking))
            elif isinstance(block, BetaTextBlock):
                # TODO: When citations are present, Anthropic splits the text
                # response into multiple text blocks, some of them with citations
                # content. This is making the rendering right now a bit strange.
                content.append(TextBlockResponse(text=block.text))
            elif isinstance(block, BetaToolUseBlock):
                content.append(
                    ToolInputResponse(
                        call_id=block.id,
                        environment=ToolEnvironment.LOCAL,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )
            elif isinstance(block, BetaServerToolUseBlock):
                content.append(
                    ToolInputResponse(
                        call_id=block.id,
                        environment=ToolEnvironment.SERVER,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )
            elif isinstance(block, BetaWebSearchToolResultBlock):
                # TODO: Maybe rename to a dedicated ToolWebSearchOutputResponse?
                if isinstance(block.content, BetaWebSearchToolResultError):
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
