from gi.repository import GObject


class AgentState(GObject.GEnum):
    __gtype_name__ = "AgentState"
    INITIALIZING = 1
    READY = 2
    RUNNING = 3
    COMPLETED = 4
