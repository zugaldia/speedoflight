from enum import Enum
from typing import Dict, List, Union

from gi.repository import GObject  # type: ignore
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel


class AppConfig(BaseModel):
    model: str = "ollama:llama3.2"  # Default to local
    mcp_servers: Dict[str, Dict[str, Union[str, Dict[str, str], List[str]]]] = {}
    agent_debug: bool = False


class MessageRole(Enum):
    SYSTEM = "system"
    HUMAN = "human"
    AI = "ai"
    TOOL = "tool"


class GBaseMessage(GObject.Object):
    def __init__(self, data: BaseMessage):
        super().__init__()
        self.data = data


class AgentRequest(BaseModel):
    session_id: str
    message: HumanMessage
