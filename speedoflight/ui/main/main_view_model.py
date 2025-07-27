import random

from gi.repository import GObject  # type: ignore

from speedoflight.constants import (
    AGENT_READY_SIGNAL,
    AGENT_RUN_COMPLETED_SIGNAL,
    AGENT_RUN_STARTED_SIGNAL,
    AGENT_UPDATE_AI_SIGNAL,
    AGENT_UPDATE_TOOL_SIGNAL,
)
from speedoflight.models import AgentResponse
from speedoflight.services.orchestrator.orchestrator_service import OrchestratorService
from speedoflight.ui.base_view_model import BaseViewModel
from speedoflight.ui.main.agent_state import AgentState
from speedoflight.ui.main.main_view_state import MainViewState


class MainViewModel(BaseViewModel):
    __gsignals__ = {
        AGENT_UPDATE_AI_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        AGENT_UPDATE_TOOL_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    AGENTIC_UPDATES = [
        "Agenting...",
        "Assembling...",
        "Analyzing...",
        "Brewing...",
        "Compiling...",
        "Computing...",
        "Conjuring...",
        "Looping...",
        "Orchestrating...",
        "Pondering...",
        "Thinking...",
        "Vibing...",
    ]

    def __init__(self, orchestrator: OrchestratorService):
        super().__init__()
        self.view_state = MainViewState()
        self._orchestrator = orchestrator
        self._orchestrator.connect(AGENT_READY_SIGNAL, self._on_agent_ready)
        self._orchestrator.connect(AGENT_RUN_STARTED_SIGNAL, self._on_agent_started)
        self._orchestrator.connect(AGENT_RUN_COMPLETED_SIGNAL, self._on_agent_completed)
        self._orchestrator.connect(AGENT_UPDATE_AI_SIGNAL, self._on_agent_update_ai)
        self._orchestrator.connect(AGENT_UPDATE_TOOL_SIGNAL, self._on_agent_update_tool)

    def _on_agent_ready(self, _: OrchestratorService):
        self.view_state.status_text = "Ready."
        self.view_state.agent_state = AgentState.READY
        self.view_state.input_enabled = True
        self.view_state.activity_mode = False

    def _on_agent_started(self, _: OrchestratorService):
        self.view_state.agent_state = AgentState.RUNNING
        self.view_state.status_text = random.choice(self.AGENTIC_UPDATES)
        self.view_state.input_enabled = False
        self.view_state.activity_mode = True

    def _on_agent_completed(self, _: OrchestratorService, encoded_message: str):
        self.view_state.agent_state = AgentState.COMPLETED
        self.view_state.input_enabled = True
        self.view_state.activity_mode = False
        response = AgentResponse.model_validate_json(encoded_message)
        if response.is_error:
            error_msg = response.message or "Unknown error occurred"
            self.view_state.status_text = error_msg
        else:
            self.view_state.status_text = "Done."

    def _on_agent_update_ai(self, _: OrchestratorService, encoded_message: str):
        self.emit(AGENT_UPDATE_AI_SIGNAL, encoded_message)

    def _on_agent_update_tool(self, _: OrchestratorService, encoded_message: str):
        self.emit(AGENT_UPDATE_TOOL_SIGNAL, encoded_message)

    def run_agent(self, text: str):
        self.view_state.status_text = "Starting agent."
        self._orchestrator.run_agent(text)

    def shutdown(self):
        pass
