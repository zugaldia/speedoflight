from abc import abstractmethod
from typing import Any

from mcp import types

from speedoflight.models import BaseMessage, ResponseMessage
from speedoflight.services.base_service import BaseService


class BaseLlmService(BaseService):
    def __init__(self, service_name: str):
        super().__init__(service_name=service_name)

    @abstractmethod
    async def generate_message(
        self,
        app_messages: list[BaseMessage],
        mcp_tools: dict[str, list[types.Tool]],
    ) -> ResponseMessage:
        """Generate a message response from the LLM provider."""
        pass

    @abstractmethod
    def to_native(self, app_msg: BaseMessage) -> Any:
        """Convert any BaseMessage to provider's native message format."""
        pass

    @abstractmethod
    def from_native(self, native_msg: Any) -> ResponseMessage:
        """Convert provider's native message format to a ResponseMessage."""
        pass
