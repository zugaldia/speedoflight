import base64
import pickle
from enum import Enum
from typing import Any, Dict, List, TypeVar, Union

from gi.repository import GObject  # type: ignore
from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel


class AppConfig(BaseModel):
    model: str = "ollama:llama3.2"  # Default to local
    mcp_servers: Dict[str, Dict[str, Union[str, Dict[str, str], List[str]]]] = {}


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


T = TypeVar("T", bound="BaseAgentResponse")


class BaseAgentResponse(BaseModel):
    def encode(self) -> str:
        data_bytes = pickle.dumps(self)
        return base64.b64encode(data_bytes).decode("utf-8")

    @classmethod
    def decode(cls: type[T], encoded_str: str) -> T:
        data_bytes = base64.b64decode(encoded_str.encode("utf-8"))
        return pickle.loads(data_bytes)


class AgentUpdateResponse(BaseAgentResponse):
    data: Any  # Raw LangGraph event data
