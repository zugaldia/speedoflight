from typing import Callable

from mcp.client.streamable_http import streamablehttp_client
from pydantic import BaseModel

from speedoflight.services.mcp.base_server import BaseServer


class StreamableHttpConfiguration(BaseModel):
    url: str
    headers: dict[str, str] | None = None


class StreamableHttpServer(BaseServer):
    def __init__(self, server_name: str, configuration: StreamableHttpConfiguration):
        super().__init__(server_name=server_name)
        self._configuration = configuration
        self._session_id_callback: Callable[[], str | None] | None = None

    async def initialize(self):
        try:
            (
                read_stream,
                write_stream,
                session_id_callback,
            ) = await self._exit_stack.enter_async_context(
                streamablehttp_client(
                    url=self._configuration.url,
                    headers=self._configuration.headers,
                )
            )

            self._session_id_callback = session_id_callback
            await self._initialize_session(read_stream, write_stream)
            self._logger.info(f"{self.server_name} HTTP server initialized.")
        except Exception as e:
            self._logger.error(f"Error initializing {self.server_name}: {e}")
            await self.shutdown()

    def get_session_id(self) -> str | None:
        if not self._session_id_callback:
            raise RuntimeError("Session ID callback is not set.")
        return self._session_id_callback()
