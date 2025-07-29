from abc import abstractmethod
from datetime import datetime
from typing import Any

from mcp import types

from speedoflight.constants import APPLICATION_NAME
from speedoflight.models import BaseMessage, ResponseMessage
from speedoflight.services.base_service import BaseService
from speedoflight.services.llm.prompts import SYSTEM_PROMPT


class BaseLlmService(BaseService):
    def __init__(self, service_name: str):
        super().__init__(service_name=service_name)

    def _get_system_prompt(self) -> str:
        """Get the system/developer prompt for the LLM."""
        today_date = datetime.now().strftime("%B %d, %Y")
        return SYSTEM_PROMPT.format(
            APPLICATION_NAME=APPLICATION_NAME, TODAY_DATE=today_date
        )

    @abstractmethod
    async def generate_message(
        self,
        app_messages: list[BaseMessage],
        tools: list[types.Tool],
    ) -> ResponseMessage:
        """Generate a message response from the LLM provider."""
        pass

    @abstractmethod
    def to_native(self, app_msg: BaseMessage) -> Any:
        """Convert human/tool-generated messages to the AI's native message format."""
        pass

    @abstractmethod
    def from_native(self, native_msg: Any) -> ResponseMessage:
        """Convert AI's native message format to an application ResponseMessage."""
        pass
