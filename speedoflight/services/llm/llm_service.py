from mcp import types

from speedoflight.models import (
    AnthropicConfig,
    BaseMessage,
    LLMProvider,
    OllamaConfig,
    ResponseMessage,
)
from speedoflight.services.base_service import BaseService
from speedoflight.services.configuration import ConfigurationService
from speedoflight.services.llm.anthropic_llm import AnthropicLlm
from speedoflight.services.llm.base_llm import BaseLlmService
from speedoflight.services.llm.ollama_llm import OllamaLlm


class LlmService(BaseService):
    def __init__(self, configuration: ConfigurationService):
        super().__init__(service_name="llm")
        self._configuration = configuration
        self._client = self._create_llm_client()
        self._logger.info("Initialized.")

    def _create_llm_client(self) -> BaseLlmService:
        """Create the appropriate LLM client based on configuration."""
        config = self._configuration.config
        provider_key = config.llm.value
        base_config = config.llms.get(provider_key, None)

        # Provider selection
        if config.llm == LLMProvider.ANTHROPIC:
            llm_config = (
                base_config
                if isinstance(base_config, AnthropicConfig)
                else AnthropicConfig()
            )
            return AnthropicLlm(llm_config)
        else:
            # Default to Ollama
            llm_config = (
                base_config if isinstance(base_config, OllamaConfig) else OllamaConfig()
            )
            return OllamaLlm(llm_config)

    async def generate_message(
        self,
        app_messages: list[BaseMessage],
        tools: dict[str, list[types.Tool]],
    ) -> ResponseMessage:
        return await self._client.generate_message(app_messages, tools)

    def shutdown(self):
        pass
