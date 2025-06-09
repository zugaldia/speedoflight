import random

from gi.repository import GObject  # type: ignore

from speedoflight.constants import (
    AGENT_MESSAGE_SIGNAL,
    AGENT_READY_SIGNAL,
    AGENT_RUN_COMPLETED_SIGNAL,
    AGENT_RUN_STARTED_SIGNAL,
)
from speedoflight.models import GBaseMessage
from speedoflight.services.orchestrator.orchestrator_service import OrchestratorService
from speedoflight.ui.base_view_model import BaseViewModel
from speedoflight.ui.main.agent_state import AgentState
from speedoflight.ui.main.main_view_state import MainViewState


class MainViewModel(BaseViewModel):
    __gsignals__ = {
        AGENT_MESSAGE_SIGNAL: (GObject.SignalFlags.RUN_FIRST, None, (object,))
    }

    AGENTIC_UPDATES = [
        "Agenting...",
        "Analyzing...",
        "Brewing...",
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
        self._orchestrator.connect(AGENT_RUN_STARTED_SIGNAL, self._on_agent_run_started)
        self._orchestrator.connect(
            AGENT_RUN_COMPLETED_SIGNAL, self._on_agent_run_completed
        )
        self._orchestrator.connect(AGENT_MESSAGE_SIGNAL, self._on_agent_message)

    def _on_agent_ready(self, orchestrator: OrchestratorService, tool_count: int):
        self.view_state.status_text = f"Ready ({tool_count} tools)."
        self.view_state.agent_state = AgentState.READY
        self.view_state.input_enabled = True
        self.view_state.activity_mode = False

    def _on_agent_run_started(self, orchestrator: OrchestratorService):
        self.view_state.agent_state = AgentState.RUNNING
        self.view_state.status_text = random.choice(self.AGENTIC_UPDATES)
        self.view_state.input_enabled = False
        self.view_state.activity_mode = True

    def _on_agent_run_completed(self, orchestrator: OrchestratorService):
        self.view_state.agent_state = AgentState.COMPLETED
        self.view_state.status_text = "Done."
        self.view_state.input_enabled = True
        self.view_state.activity_mode = False

    def _on_agent_message(
        self, orchestrator: OrchestratorService, message: GBaseMessage
    ):
        self.emit(AGENT_MESSAGE_SIGNAL, message)

    def run_agent(self, text: str):
        self.view_state.status_text = "Starting agent."
        self._orchestrator.run_agent(text)

    def shutdown(self):
        pass
