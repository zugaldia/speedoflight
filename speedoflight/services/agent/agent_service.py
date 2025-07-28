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
    AgentResponse,
    BaseMessage,
    ImageMimeType,
    MessageRole,
    RequestMessage,
    ResponseMessage,
    SolMessage,
    StopReason,
    ToolImageOutputRequest,
    ToolTextOutputRequest,
)
from speedoflight.services.base_service import BaseService
from speedoflight.services.configuration import ConfigurationService
from speedoflight.services.history import HistoryService
from speedoflight.services.llm.llm_service import LlmService
from speedoflight.services.mcp.mcp_service import McpService


class AgentService(BaseService):
    __gsignals__ = {
        AGENT_READY_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
        AGENT_RUN_STARTED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
        AGENT_RUN_COMPLETED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        AGENT_UPDATE_AI_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        AGENT_UPDATE_TOOL_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(
        self,
        configuration: ConfigurationService,
        llm: LlmService,
        history: HistoryService,
        mcp: McpService,
    ):
        super().__init__(service_name="agent")
        self._configuration = configuration
        self._llm = llm
        self._history = history
        self._mcp = mcp
        self._session_id: str | None = None
        self._setup()
        self._logger.info("Initialized.")

    def set_session_id(self, session_id: str):
        """Set the session ID for this agent and share it with the history service."""
        self._session_id = session_id
        self._history.set_session_id(session_id)
        self._logger.info(f"Session ID set to: {session_id}")

    def shutdown(self):
        pass

    def _add_message(self, message: BaseMessage):
        """Add a message to the conversation history and notify the UI."""
        self._history.add_message(message)
        if message.role == MessageRole.AI:
            self.safe_emit(AGENT_UPDATE_AI_SIGNAL, message.model_dump_json())
        elif message.role == MessageRole.TOOL:
            self.safe_emit(AGENT_UPDATE_TOOL_SIGNAL, message.model_dump_json())

    def _setup(self):
        self._logger.info("Setting up agent.")
        self.safe_emit(AGENT_READY_SIGNAL)

    async def run(self, request: AgentRequest):
        self._logger.info(f"Running agent with request: {request}")
        self.safe_emit(AGENT_RUN_STARTED_SIGNAL)
        self._add_message(request.message)
        await self._run_llm()

    def _emit_error(self, error_message: str):
        agent_response = AgentResponse(
            is_error=True,
            message=SolMessage(
                role=MessageRole.SOL,
                message=error_message,
            ),
        )
        self.safe_emit(AGENT_RUN_COMPLETED_SIGNAL, agent_response.model_dump_json())

    async def _run_llm(self):
        total_messages = len(self._history.messages)
        total_tools = len(self._mcp.tools)
        self._logger.info(
            f"Running agent with {total_messages} messages and {total_tools} tools."
        )

        try:
            message = await self._llm.generate_message(
                self._history.messages, self._mcp.tools
            )
            self._add_message(message)
            await self._handle_response(message)
        except Exception as e:
            self._emit_error(f"Error during LLM generation: {e}")

    async def _handle_response(self, message: ResponseMessage):
        if message.stop_reason == StopReason.END_TURN:
            response = AgentResponse(is_error=False)
            self.safe_emit(AGENT_RUN_COMPLETED_SIGNAL, response.model_dump_json())
        elif message.stop_reason == StopReason.TOOL_USE:
            try:
                self._logger.info("Tool call detected, processing tool.")
                await self._handle_tool_use(message)
            except Exception as e:
                self._emit_error(f"Error during tool processing: {e}")
        else:
            self._emit_error(f"Unhandled stop reason: {message.stop_reason}")

    async def _handle_tool_use(self, message: ResponseMessage):
        tool_result = await self._mcp.call_tool(message)
        if tool_result is None:
            self._emit_error("Tool call returned no result.")
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
