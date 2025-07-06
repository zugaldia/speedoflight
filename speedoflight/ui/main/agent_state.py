from gi.repository import GObject  # type: ignore


class AgentState(GObject.GEnum):
    INITIALIZING = 1
    READY = 2
    RUNNING = 3
    COMPLETED = 4
