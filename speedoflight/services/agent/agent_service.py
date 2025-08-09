from gi.repository import GObject  # type: ignore
from mcp import types

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
    ToolInputResponse,
    ToolTextOutputRequest,
)
from speedoflight.services.base_service import BaseService
from speedoflight.services.configuration import ConfigurationService
from speedoflight.services.desktop import DesktopService
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
        desktop: DesktopService,
        llm: LlmService,
        history: HistoryService,
        mcp: McpService,
    ):
        super().__init__(service_name="agent")
        self._configuration = configuration
        self._desktop = desktop
        self._llm = llm
        self._history = history
        self._mcp = mcp
        self._session_id: str | None = None
        self._current_iterations = 0
        self._setup()
        self._logger.info("Initialized.")

    def set_session_id(self, session_id: str):
        """Set the session ID for this agent and share it with the history service."""
        self._session_id = session_id
        self._history.set_session_id(session_id)

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
        self._logger.info(f"Running agent with session ID: {request.session_id}")
        self._current_iterations = 0
        self.safe_emit(AGENT_RUN_STARTED_SIGNAL)
        self._add_message(request.message)
        await self._run_llm()

    async def _run_llm(self):
        try:
            self._current_iterations += 1
            max_iterations = self._configuration.config.max_iterations
            if self._current_iterations > max_iterations:
                raise ValueError(
                    f"Maximum iterations limit reached ({max_iterations}). "
                    "The agent may be stuck in a loop."
                )

            # Good to proceed
            self._logger.info(f"LLM run {self._current_iterations}/{max_iterations}")
            mcp_tools = [tool for tools in self._mcp.tools.values() for tool in tools]
            tools = mcp_tools + self._desktop.get_tools()
            message = await self._llm.generate_message(self._history.messages, tools)
            self._add_message(message)
            await self._handle_response(message)
        except Exception as e:
            # This breaks the loop. Under which circumstances could we continue?
            agent_response = AgentResponse(
                is_error=True,
                message=SolMessage(
                    role=MessageRole.SOL,
                    message=f"Error during LLM run ({self._current_iterations}/{self._configuration.config.max_iterations}): {e}",
                ),
            )
            self.safe_emit(AGENT_RUN_COMPLETED_SIGNAL, agent_response.model_dump_json())

    async def _handle_response(self, message: ResponseMessage):
        if message.stop_reason == StopReason.END_TURN:
            response = AgentResponse(is_error=False)
            self.safe_emit(AGENT_RUN_COMPLETED_SIGNAL, response.model_dump_json())
        elif message.stop_reason == StopReason.TOOL_USE:
            self._logger.info("Tool call detected, invoking tool.")
            await self._handle_tool_use(message)
        else:
            raise ValueError(f"Unhandled stop reason: {message.stop_reason}")

    async def _handle_tool_use(self, message: ResponseMessage):
        tool_inputs = [
            content
            for content in message.content
            if isinstance(content, ToolInputResponse)
        ]

        # Currently, we assume that one and only one tool input is present in
        # each message. Parallel tool invocation is not supported.
        # See e.g. Anthropic's ToolChoiceAutoParam.
        if len(tool_inputs) == 0:
            raise ValueError("Stop reason was tool use but no tool input was provided.")
        elif len(tool_inputs) > 1:
            self._logger.warning(
                "Multiple tool inputs found, only the first one will be processed."
            )

        tool_input = tool_inputs[0]

        # Always add a message before invoking the LLM again. Otherwise, the
        # chain will be broken because LLMs like Anthropic expect a tool result
        # for every tool request. Additionally, the tool invocations try to
        # surface error messages by design as much as possible (rather than
        # swallowing/logging them) to pass them back to the LLM to inform its
        # execution.
        if self._desktop.is_tool(tool_input.name):
            self._logger.info(f"Handling desktop tool: {tool_input.name}")
            request_message = await self._handle_desktop_tool_use(tool_input)
            self._add_message(request_message)
        else:
            self._logger.info(f"Handling MCP tool: {tool_input.name}")
            request_message = await self._handle_mcp_tool_use(tool_input)
            self._add_message(request_message)

        await self._run_llm()

    async def _handle_desktop_tool_use(
        self, tool_input: ToolInputResponse
    ) -> RequestMessage:
        return await self._desktop.call_tool(tool_input)

    async def _handle_mcp_tool_use(
        self, tool_input: ToolInputResponse
    ) -> RequestMessage:
        tool_result = await self._mcp.call_tool(tool_input)

        # Anthropic requires each `tool_use` must have a single `tool_result`
        # for a given `call_id`. We use this loop to consolidate potentially
        # multiple responses of the same type into one message. ElevenLabs
        # does this, for example, when you ask for voices available in your
        # account, it returns 10 individual voice results (for the same call)
        text: list[str] = []
        images = []
        for block in tool_result.content:
            if isinstance(block, types.TextContent):
                text.append(block.text)
            elif isinstance(block, types.ImageContent):
                images.append((block.data, block.mimeType))
            else:
                self._logger.warning(
                    f"Unsupported tool result block type: {block.type}"
                )

        if tool_result.structured_content is not None:
            self._logger.warning(
                "Tool result contains structured content, which is not supported."
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
            return RequestMessage(
                role=MessageRole.TOOL,
                content=[
                    ToolTextOutputRequest(
                        call_id=tool_result.call_id,
                        name=tool_result.name,
                        text=tool_text,
                        is_error=tool_result.is_error,
                    )
                ],
            )

        elif images:
            image_data, image_mime_type = images[0]
            return RequestMessage(
                role=MessageRole.TOOL,
                content=[
                    ToolImageOutputRequest(
                        call_id=tool_result.call_id,
                        name=tool_result.name,
                        data=image_data,
                        mime_type=ImageMimeType(image_mime_type),
                        is_error=tool_result.is_error,
                    )
                ],
            )
        else:
            message = "Tool returned no output or unsupported content types."
            return RequestMessage(
                role=MessageRole.TOOL,
                content=[
                    ToolTextOutputRequest(
                        call_id=tool_result.call_id,
                        name=tool_result.name,
                        text=message,
                        is_error=tool_result.is_error,
                    )
                ],
            )
