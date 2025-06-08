import asyncio
import threading

from gi.repository import GObject  # type: ignore
from langchain_core.messages import HumanMessage

from speedoflight.constants import (
    AGENT_MESSAGE_SIGNAL,
    AGENT_READY_SIGNAL,
    AGENT_RUN_COMPLETED_SIGNAL,
    AGENT_RUN_STARTED_SIGNAL,
    AGENT_UPDATE_SIGNAL,
)
from speedoflight.models import AgentRequest, AgentUpdateResponse, GBaseMessage
from speedoflight.services.agent.agent_service import AgentService
from speedoflight.services.base_service import BaseService
from speedoflight.services.configuration.configuration_service import (
    ConfigurationService,
)
from speedoflight.utils import generate_uuid


class OrchestratorService(BaseService):
    __gsignals__ = {
        AGENT_MESSAGE_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (GBaseMessage,)),
        AGENT_READY_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
        AGENT_RUN_STARTED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
        AGENT_RUN_COMPLETED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, configuration: ConfigurationService, agent: AgentService):
        super().__init__(service_name="orchestrator")

        # TODO: Eventually integrate with Asyncio support for PyGObject (experimental)
        # https://pygobject.gnome.org/guide/asynchronous.html
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._loop_thread.start()

        self._session_id = generate_uuid()

        self._agent = agent
        self._agent.connect(AGENT_UPDATE_SIGNAL, self._on_agent_update)
        self._agent.connect(AGENT_READY_SIGNAL, self._on_agent_ready)
        self._agent.connect(AGENT_RUN_STARTED_SIGNAL, self._on_agent_run_started)
        self._agent.connect(AGENT_RUN_COMPLETED_SIGNAL, self._on_agent_run_completed)
        self._load_tools()

        self._logger.info("Initialized")

    def _run_async_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _load_tools(self):
        self._logger.info("Loading MCP tools.")
        asyncio.run_coroutine_threadsafe(self._agent.load_tools_async(), self._loop)

    def run_agent(self, message: str):
        human_message = HumanMessage(content=message)
        request = AgentRequest(
            session_id=self._session_id,
            message=human_message,
        )

        self._logger.info("Running agent.")
        asyncio.run_coroutine_threadsafe(self._agent.stream_async(request), self._loop)

    def _on_agent_update(self, agent_service, encoded_object: str):
        try:
            # Extract messages from the agent update data
            # E.g. AI response: {"agent": {"messages": [AIMessage(...)]}}
            # E.g. tool response: {'tools': {'messages': [ToolMessage(...)]}}
            self._logger.info("Agent update received.")
            update_response = AgentUpdateResponse.decode(encoded_object)
            for node_name, node_data in update_response.data.items():
                if isinstance(node_data, dict) and "messages" in node_data:
                    messages = node_data["messages"]
                    for message in messages:
                        g_message = GBaseMessage(data=message)
                        self._logger.info(f"Emitting {node_name} message.")
                        self.safe_emit(AGENT_MESSAGE_SIGNAL, g_message)
        except Exception as e:
            self._logger.error(f"Error processing agent update: {e}")

    def _on_agent_ready(self, agent_service):
        self._logger.info("Agent is ready.")
        self.safe_emit(AGENT_READY_SIGNAL)

    def _on_agent_run_started(self, agent_service):
        self._logger.info("Agent run started.")
        self.safe_emit(AGENT_RUN_STARTED_SIGNAL)

    def _on_agent_run_completed(self, agent_service):
        self._logger.info("Agent run completed.")
        self.safe_emit(AGENT_RUN_COMPLETED_SIGNAL)

    def shutdown(self):
        self._logger.info("Shutting down.")
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=5.0)
