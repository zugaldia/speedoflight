from typing import Optional

from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

from speedoflight.services.mcp.base_server import BaseServer

DEFAULT_ENCODING = "utf-8"
DEFAULT_ENCODING_ERROR_HANDLER = "strict"


class StdioConfiguration(BaseModel):
    command: str
    args: list[str] = []
    env: Optional[dict[str, str]] = None


class StdioServer(BaseServer):
    def __init__(self, server_name: str, configuration: StdioConfiguration):
        super().__init__(server_name=server_name)
        self._configuration = configuration

    async def initialize(self):
        try:
            parameters = StdioServerParameters(
                command=self._configuration.command,
                args=self._configuration.args,
                env=self._configuration.env,
                encoding=DEFAULT_ENCODING,
                encoding_error_handler=DEFAULT_ENCODING_ERROR_HANDLER,
            )

            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(server=parameters)
            )

            await self._initialize_session(read_stream, write_stream)
            self._logger.info(f"{self.server_name} stdio server initialized.")
        except Exception as e:
            self._logger.error(f"Error initializing {self.server_name}: {e}")
            await self.shutdown()
