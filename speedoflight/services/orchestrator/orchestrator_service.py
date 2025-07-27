import asyncio

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
    MessageRole,
    RequestMessage,
    TextBlockRequest,
)
from speedoflight.services.agent.agent_service import AgentService
from speedoflight.services.base_service import BaseService
from speedoflight.services.configuration.configuration_service import (
    ConfigurationService,
)
from speedoflight.utils import generate_uuid


class OrchestratorService(BaseService):
    __gsignals__ = {
        AGENT_UPDATE_AI_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        AGENT_UPDATE_TOOL_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        AGENT_READY_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
        AGENT_RUN_STARTED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
        AGENT_RUN_COMPLETED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(
        self,
        configuration: ConfigurationService,
        agent: AgentService,
    ):
        super().__init__(service_name="orchestrator")
        self._session_id = generate_uuid()

        self._agent = agent
        self._agent.connect(AGENT_UPDATE_AI_SIGNAL, self._on_agent_update_ai)
        self._agent.connect(AGENT_UPDATE_TOOL_SIGNAL, self._on_agent_update_tool)
        self._agent.connect(AGENT_READY_SIGNAL, self._on_agent_ready)
        self._agent.connect(AGENT_RUN_STARTED_SIGNAL, self._on_agent_run_started)
        self._agent.connect(AGENT_RUN_COMPLETED_SIGNAL, self._on_agent_run_completed)

        self._agent_task: asyncio.Task | None = None

        self._logger.info("-> Initialized.")

    def run_agent(self, message: str):
        self._logger.info("Running agent.")
        request = AgentRequest(
            session_id=self._session_id,
            message=RequestMessage(
                role=MessageRole.HUMAN,
                content=[
                    TextBlockRequest(text=message),
                ],
            ),
        )

        # TODO: Make the agent task cancellable from the UI
        self._agent_task = asyncio.create_task(self._agent.run(request))
        self._agent_task.add_done_callback(self._on_agent_task_done)
        self._logger.info("Agent task started.")

    def _on_agent_task_done(self, future: asyncio.Future):
        try:
            future.result()
            self._logger.info("Agent execution completed.")
        except Exception as e:
            self._logger.error(f"Agent execution failed: {e}")

    def _on_agent_update_ai(self, agent_service, encoded_message: str):
        self._logger.info("Emitting AI message.")
        self.safe_emit(AGENT_UPDATE_AI_SIGNAL, encoded_message)

    def _on_agent_update_tool(self, agent_service, encoded_message: str):
        self._logger.info("Emitting tool message.")
        self.safe_emit(AGENT_UPDATE_TOOL_SIGNAL, encoded_message)

    def _on_agent_ready(self, agent_service):
        self._logger.info("Agent is ready.")
        self.safe_emit(AGENT_READY_SIGNAL)

    def _on_agent_run_started(self, agent_service):
        self._logger.info("Agent run started.")
        self.safe_emit(AGENT_RUN_STARTED_SIGNAL)

    def _on_agent_run_completed(self, agent_service, encoded_message: str):
        self._logger.info("Agent run completed.")
        self.safe_emit(AGENT_RUN_COMPLETED_SIGNAL, encoded_message)

    def shutdown(self):
        self._logger.info("Shutting down.")
        if self._agent_task and not self._agent_task.done():
            self._logger.info("Cancelling agent task.")
            self._agent_task.cancel()
