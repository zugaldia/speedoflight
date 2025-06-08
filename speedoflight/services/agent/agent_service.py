from typing import Any, AsyncIterator, List, Optional

from gi.repository import GObject  # type: ignore
from langchain.chat_models import init_chat_model
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

from speedoflight.constants import (
    AGENT_READY_SIGNAL,
    AGENT_RUN_COMPLETED_SIGNAL,
    AGENT_RUN_STARTED_SIGNAL,
    AGENT_UPDATE_SIGNAL,
)
from speedoflight.models import AgentRequest, AgentUpdateResponse
from speedoflight.services.base_service import BaseService
from speedoflight.services.configuration.configuration_service import (
    ConfigurationService,
)


class AgentService(BaseService):
    __gsignals__ = {
        AGENT_UPDATE_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        AGENT_READY_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        AGENT_RUN_STARTED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
        AGENT_RUN_COMPLETED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, configuration: ConfigurationService):
        super().__init__(service_name="agent")
        self._app_config = configuration.get_config()
        self._agent: Optional[CompiledGraph] = None
        self._mcp_tools: List[BaseTool] = []
        self._logger.info("Initialized.")

    async def load_tools_async(self):
        self._logger.info("Loading MCP tools.")
        client = MultiServerMCPClient(self._app_config.mcp_servers)
        self._mcp_tools = await client.get_tools()
        tool_names = [tool.name for tool in self._mcp_tools]
        self._logger.info(f"Loaded {len(self._mcp_tools)} tools: {tool_names}")
        self._setup_agent()

    def _setup_agent(self):
        self._logger.info("Setting up agent.")
        model = init_chat_model(self._app_config.model, temperature=0)
        checkpointer = InMemorySaver()
        self._agent = create_react_agent(
            model,
            tools=self._mcp_tools,
            checkpointer=checkpointer,
            debug=False,
        )
        self._logger.info("Agent is ready.")
        self.safe_emit(AGENT_READY_SIGNAL, len(self._mcp_tools))

    async def stream_async(self, request: AgentRequest):
        if self._agent is None:
            # TODO: The UI should disable the button if the agent is not initialized
            self._logger.error("Agent not initialized.")
            return

        self._logger.info("Agent run started.")
        self.safe_emit(AGENT_RUN_STARTED_SIGNAL)

        config = {"configurable": {"thread_id": request.session_id}}
        events: AsyncIterator[dict[str, Any] | Any] = self._agent.astream(
            input={"messages": [request.message]},
            config=config,
            stream_mode=["updates"],
            debug=False,
        )

        async for event_type, event in events:
            # self._logger.info(f"Agent event: {event}")
            if event_type == "updates":
                update = AgentUpdateResponse(data=event)
                encoded = update.encode()
                self.safe_emit(AGENT_UPDATE_SIGNAL, encoded)
            else:
                self._logger.warning(f"Unknown event type: {event_type}")

        self._logger.info("Agent run completed.")
        self.safe_emit(AGENT_RUN_COMPLETED_SIGNAL)

    def shutdown(self):
        self._logger.info("Shutting down.")
