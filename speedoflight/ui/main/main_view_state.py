from gi.repository import GObject  # type: ignore

from speedoflight.ui.base_view_state import BaseViewState
from speedoflight.ui.main.agent_state import AgentState


class MainViewState(BaseViewState):
    status_text = GObject.Property(type=str, default="")
    agent_state = GObject.Property(type=AgentState, default=AgentState.INITIALIZING)
    input_enabled = GObject.Property(type=bool, default=False)
    activity_mode = GObject.Property(type=bool, default=False)
    enable_computer_use = GObject.Property(type=bool, default=False)
