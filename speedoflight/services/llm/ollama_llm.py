from typing import Any, Mapping, Sequence

from mcp import types
from ollama import (
    AsyncClient,
    ChatResponse,
    ListResponse,
    Message,
    Options,
    ShowResponse,
)

from speedoflight.models import (
    BaseMessage,
    MessageRole,
    OllamaConfig,
    RequestMessage,
    ResponseMessage,
    StopReason,
    TextBlockRequest,
    TextBlockResponse,
    ToolEnvironment,
    ToolImageOutputRequest,
    ToolInputResponse,
    ToolTextOutputRequest,
    Usage,
)
from speedoflight.services.llm.base_llm import BaseLlmService
from speedoflight.utils import generate_uuid


class OllamaLlm(BaseLlmService):
    def __init__(self, config: OllamaConfig):
        super().__init__(service_name="ollama")
        self._config = config
        self._logger.info(f"Using Ollama config: {config}")
        self._client = AsyncClient(host=config.host)

    async def generate_message(
        self,
        app_messages: list[BaseMessage],
        mcp_tools: dict[str, list[types.Tool]],
    ) -> ResponseMessage:
        messages = [self.to_native(msg) for msg in app_messages]
        tools: Sequence[Mapping[str, Any]] = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tools_list in mcp_tools.values()
            for tool in tools_list
        ]

        result: ChatResponse = await self._client.chat(
            model=self._config.model,
            options=Options(temperature=self._config.temperature),
            messages=messages,
            tools=tools,
        )

        # self._logger.info(f"Generated message: {result}")
        return self.from_native(result)

    async def list_supported_models(self):
        models: ListResponse = await self._client.list()
        for model in models.models:
            model_name = model.model
            if not model_name:
                continue
            show: ShowResponse = await self._client.show(model_name)
            has_tools = "tools" in show.capabilities if show.capabilities else False
            if has_tools:
                self._logger.info(f"- Available model: {model_name} (supports tools)")

    def to_native(self, app_msg: BaseMessage) -> Mapping[str, Any] | Message:
        if isinstance(app_msg, ResponseMessage) and app_msg.raw is not None:
            return Message(
                role=app_msg.raw.role,
                content=app_msg.raw.content,
            )

        if app_msg.role == MessageRole.HUMAN:
            role = "user"
        elif app_msg.role == MessageRole.TOOL:
            role = "tool"
        else:
            raise ValueError(f"Unsupported message role: {app_msg.role}")

        content = app_msg.content if isinstance(app_msg, RequestMessage) else []
        if len(content) != 1:
            # TODO: Do we need to convert the application message into
            # multiple native messages in this situation?
            self._logger.warning("Only one content block is supported in Ollama.")

        block = next(iter(content), None)
        if isinstance(block, TextBlockRequest):
            return Message(role=role, content=block.text)
        elif isinstance(block, ToolTextOutputRequest):
            # Ollama's native Message does not support tool output!?
            return {"role": "tool", "content": block.text, "tool_name": block.name}
        elif isinstance(block, ToolImageOutputRequest):
            # Is there a better way to handle this?
            return {
                "role": "tool",
                "content": f"Image generated ({block.mime_type.value}) and already shown to the user.",
                "tool_name": block.name,
            }
        else:
            raise ValueError(f"Unsupported application block type: {type(block)}")

    def from_native(self, native_msg: ChatResponse) -> ResponseMessage:
        stop_reason = StopReason.END_TURN
        if native_msg.done:
            if native_msg.done_reason != "stop":
                self._logger.warning(
                    # Ollama always uses stop even when it detects a tool calling
                    f"Unexpected done reason: {native_msg.done_reason}."
                )
        else:
            # It should always be done because we are not streaming results (yet?)
            self._logger.warning("Message should be done, we are not streaming.")

        content = []
        if native_msg.message.content:
            content.append(TextBlockResponse(text=native_msg.message.content))
        if native_msg.message.tool_calls:
            stop_reason = StopReason.TOOL_USE
            for tool_call in native_msg.message.tool_calls:
                content.append(
                    ToolInputResponse(
                        call_id=generate_uuid(),  # Ollama does not return one
                        environment=ToolEnvironment.LOCAL,
                        name=tool_call.function.name,
                        arguments=dict(tool_call.function.arguments),
                    )
                )

        if native_msg.message.role == "assistant":
            role = MessageRole.AI
        else:
            raise ValueError(
                f"Unexpected native message role: {native_msg.message.role}"
            )

        usage = Usage(
            input_tokens=native_msg.prompt_eval_count,
            output_tokens=native_msg.eval_count,
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
