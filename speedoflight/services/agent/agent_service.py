from gi.repository import GObject  # type: ignore

from speedoflight.constants import (
    AGENT_READY_SIGNAL,
    AGENT_RUN_COMPLETED_SIGNAL,
    AGENT_RUN_STARTED_SIGNAL,
    AGENT_UPDATE_AI_SIGNAL,
    AGENT_UPDATE_TOOL_SIGNAL,
)
from speedoflight.models import (
    AgentRequest,
    BaseMessage,
    ImageMimeType,
    MessageRole,
    RequestMessage,
    ResponseMessage,
    StopReason,
    ToolImageOutputRequest,
    ToolTextOutputRequest,
)
from speedoflight.services.base_service import BaseService
from speedoflight.services.configuration import ConfigurationService
from speedoflight.services.llm.llm_service import LlmService
from speedoflight.services.mcp.mcp_service import McpService


class AgentService(BaseService):
    __gsignals__ = {
        AGENT_READY_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        AGENT_RUN_STARTED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
        AGENT_RUN_COMPLETED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
        AGENT_UPDATE_AI_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        AGENT_UPDATE_TOOL_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(
        self,
        configuration: ConfigurationService,
        llm: LlmService,
        mcp: McpService,
    ):
        super().__init__(service_name="agent")
        self._configuration = configuration
        self._llm = llm
        self._mcp = mcp

        # TODO: This is a naive implementation. We should probably create a
        # memory service where we track tokens limits and summarize old
        # history as needed.
        self._messages: list[BaseMessage] = []

        self._setup()
        self._logger.info("Initialized.")

    def shutdown(self):
        pass

    def _add_message(self, message: BaseMessage):
        """Add a message to the conversation history and notify the UI."""
        if message.role == MessageRole.AI:
            self.safe_emit(AGENT_UPDATE_AI_SIGNAL, message.model_dump_json())
        elif message.role == MessageRole.TOOL:
            self.safe_emit(AGENT_UPDATE_TOOL_SIGNAL, message.model_dump_json())

        self._messages.append(message)
        total_messages = len(self._messages)
        self._logger.info(f"Added message (total: {total_messages}): {message}")

    def _setup(self):
        self._logger.info("Setting up agent.")

        # FIXME: Update the UI as new tools are encountered.
        self.safe_emit(AGENT_READY_SIGNAL, 0)

    async def run(self, request: AgentRequest):
        self._logger.info(f"Running agent with request: {request}")
        self.safe_emit(AGENT_RUN_STARTED_SIGNAL)
        self._add_message(request.message)
        await self._run_llm()

    async def _run_llm(self):
        total_messages = len(self._messages)
        total_tools = len(self._mcp.tools)
        self._logger.info(
            f"Running agent with {total_messages} messages and {total_tools} tools."
        )

        try:
            message = await self._llm.generate_message(self._messages, self._mcp.tools)
            self._add_message(message)
            await self._handle_response(message)
        except Exception as e:
            self._logger.error(f"Error during LLM generation: {e}")

    async def _handle_response(self, message: ResponseMessage):
        if message.stop_reason == StopReason.END_TURN:
            self._logger.info("End of turn detected.")
            self.safe_emit(AGENT_RUN_COMPLETED_SIGNAL)
        elif message.stop_reason == StopReason.TOOL_USE:
            self._logger.info("Tool call detected, processing tool.")
            await self._handle_tool_use(message)
        else:
            self._logger.warning(f"Unhandled stop reason: {message.stop_reason}")

    async def _handle_tool_use(self, message: ResponseMessage):
        tool_result = await self._mcp.call_tool(message)
        if tool_result is None:
            # TODO: End turn?
            self._logger.warning("Tool call returned no result.")
            return

        # Anthropic requires each `tool_use` must have a single `tool_result`
        # for a given `call_id`. We use this loop to consolidate potentially
        # multiple responses of the same type into one message. ElevenLabs
        # does this, for example, when you ask for voices available in your
        # account, it returns 10 individual voice results (for the same call)
        text = []
        images = []
        for block in tool_result.result.content:
            if block.type == "text":
                text.append(block.text)
            elif block.type == "image":
                images.append((block.data, block.mimeType))
            else:
                self._logger.warning(
                    f"Unsupported tool result block type: {block.type}"
                )

        if text and images:
            self._logger.warning(
                "Tool result contains both text and images, which is not supported, only text will be sent."
            )
        if len(text) > 1:
            self._logger.warning(
                "Tool result contains multiple text blocks, they will be concatenated."
            )
        if len(images) > 1:
            self._logger.warning(
                "Tool result contains multiple images, only the first one will be sent."
            )

        if text:
            tool_text = text[0] if len(text) == 1 else "\n".join(text)
            self._add_message(
                RequestMessage(
                    role=MessageRole.TOOL,
                    content=[
                        ToolTextOutputRequest(
                            call_id=tool_result.call_id,
                            name=tool_result.name,
                            text=tool_text,
                            is_error=tool_result.result.isError,
                        )
                    ],
                )
            )
        elif images:
            image_data, image_mime_type = images[0]
            self._add_message(
                RequestMessage(
                    role=MessageRole.TOOL,
                    content=[
                        ToolImageOutputRequest(
                            call_id=tool_result.call_id,
                            name=tool_result.name,
                            data=image_data,
                            mime_type=ImageMimeType(image_mime_type),
                            is_error=tool_result.result.isError,
                        )
                    ],
                )
            )

        await self._run_llm()
