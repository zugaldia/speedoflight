from typing import Any, AsyncIterator, List, Optional

from gi.repository import GObject  # type: ignore
from langchain.chat_models import init_chat_model
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

from speedoflight.constants import (
    AGENT_READY_SIGNAL,
    AGENT_RUN_COMPLETED_SIGNAL,
    AGENT_RUN_STARTED_SIGNAL,
    AGENT_UPDATE_AI_SIGNAL,
    AGENT_UPDATE_TOOL_SIGNAL,
)
from speedoflight.models import AgentRequest
from speedoflight.services.base_service import BaseService
from speedoflight.services.configuration.configuration_service import (
    ConfigurationService,
)
from speedoflight.services.mcp.mcp_service import McpService


class AgentService(BaseService):
    __gsignals__ = {
        AGENT_UPDATE_AI_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        AGENT_UPDATE_TOOL_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        AGENT_READY_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        AGENT_RUN_STARTED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
        AGENT_RUN_COMPLETED_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, configuration: ConfigurationService, mcp: McpService):
        super().__init__(service_name="agent")
        self._mcp = mcp
        self._app_config = configuration.get_config()
        self._agent: Optional[CompiledGraph] = None
        self._mcp_tools: List[BaseTool] = []
        self._logger.info("Initialized.")

    async def load_tools_async(self):
        try:
            # Prints server metadata
            if self._app_config.agent_debug:
                for server_name in self._app_config.mcp_servers.keys():
                    self._logger.debug(f"Getting info for {server_name}")
                    await self._mcp.send_ping(server_name)
            self._logger.info("Loading MCP tools.")
            self._mcp_tools = await self._mcp.get_tools()
            tool_names = [tool.name for tool in self._mcp_tools]
            self._logger.info(f"Loaded {len(self._mcp_tools)} tools: {tool_names}")
            self._setup_agent()
        except Exception:
            self._logger.error("Failed to load MCP tools.", exc_info=True)

    def _setup_agent(self):
        self._logger.info("Setting up agent.")

        # For Ollama models that don't support tools, the agent fails with
        # obscure 400 errors. We need to improve this logic by checking tool
        # support first or at least capturing a more user friendly error.
        model = init_chat_model(self._app_config.model, temperature=0)

        checkpointer = InMemorySaver()
        cloud_tools = self._app_config.cloud_tools.get(self._app_config.model, [])
        all_tools = self._mcp_tools + cloud_tools

        self._agent = create_react_agent(
            model,
            tools=all_tools,
            checkpointer=checkpointer,
            debug=self._app_config.agent_debug,
        )
        self._logger.info("Agent is ready.")
        self.safe_emit(AGENT_READY_SIGNAL, len(all_tools))

    async def stream_async(self, request: AgentRequest):
        if self._agent is None:
            self._logger.error("Agent not initialized.")
            return

        self._logger.info("Agent run started.")
        self.safe_emit(AGENT_RUN_STARTED_SIGNAL)

        config = {"configurable": {"thread_id": request.session_id}}

        # Can be: "values", "updates", "debug", "messages", "custom"
        stream_mode = ["updates"]
        if self._app_config.agent_debug:
            stream_mode.append("debug")

        events: AsyncIterator[dict[str, Any] | Any] = self._agent.astream(
            input={"messages": [request.message]},
            config=config,
            stream_mode=stream_mode,
            debug=self._app_config.agent_debug,
        )

        async for event_type, event in events:
            if event_type == "updates":
                self._logger.info(f"-> Received update event: {event}")
                self._process_update(event)
            elif event_type == "debug":
                self._logger.info(f"Debug event: {event}")
            else:
                self._logger.warning(f"Unhandled event type: {event_type}: {event}")

        self._logger.info("Agent run completed.")
        self.safe_emit(AGENT_RUN_COMPLETED_SIGNAL)

    def _process_update(self, event):
        if not isinstance(event, dict):
            self._logger.warning(f"Expected dictionary, got {type(event)}")
            return

        for key in event.keys():
            if key == "agent":
                agent_data = event[key]
                if isinstance(agent_data, dict):
                    self._process_agent_update(agent_data)
                else:
                    self._logger.warning(f"Expected dictionary, got {type(agent_data)}")
            elif key == "tools":
                tools_data = event[key]
                if isinstance(tools_data, dict):
                    self._process_tools_update(tools_data)
                else:
                    self._logger.warning(f"Expected dictionary, got {type(tools_data)}")
            else:
                self._logger.warning(f"Unknown update key: {key}")

    def _process_agent_update(self, agent_data: dict):
        for agent_key in agent_data.keys():
            if agent_key == "messages":
                messages = agent_data[agent_key]
                if isinstance(messages, list):
                    for message in messages:
                        encoded = message.model_dump_json()
                        self.safe_emit(AGENT_UPDATE_AI_SIGNAL, encoded)
                else:
                    self._logger.warning(f"Expected a list, got {type(messages)}")
            else:
                self._logger.warning(f"Unknown agent update key: {agent_key}")

    def _process_tools_update(self, tools_data: dict):
        for tools_key in tools_data.keys():
            if tools_key == "messages":
                messages = tools_data[tools_key]
                if isinstance(messages, list):
                    for message in messages:
                        encoded = message.model_dump_json()
                        self.safe_emit(AGENT_UPDATE_TOOL_SIGNAL, encoded)
                else:
                    self._logger.warning(f"Expected a list, got {type(messages)}")
            else:
                self._logger.warning(f"Unknown tools update key: {tools_key}")

    def shutdown(self):
        self._logger.info("Shutting down.")
