"""

Eventually replace them all with RemoteInterface as default.
Pynput not an option because of https://github.com/moses-palmer/pynput/issues/450

"""

import asyncio

from speedoflight.services.base_service import BaseService

RESPONSE_TIMEOUT = 30.0  # seconds
TYPING_DELAY = 12  # milliseconds

SUCCESS_TEMPLATE = """
The command `{command}` was executed successfully.
(Any relative coordinate values have been converted to absolute desktop values
and might not match the original input parameters. This is expected.)
<stdout>\n{stdout}\n</stdout>
""".strip()

ERROR_TEMPLATE = """
There was a problem executing the command `{command}`.
(Any relative coordinate values have been converted to absolute desktop values
and might not match the original input parameters. This is expected.)
<return_code>{code}</return_code>
<stdout>\n{stdout}\n</stdout>
<stderr>\n{stderr}\n</stderr>
""".strip()


class CommandService(BaseService):
    def __init__(self, service_name: str):
        super().__init__(service_name=service_name)

    async def execute(self, command: str) -> tuple[bool, str]:
        self._logger.info(f"Executing command: {command}")
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=RESPONSE_TIMEOUT
        )

        code = process.returncode
        if code == 0:
            stdout_decoded = stdout.decode().strip()
            return False, SUCCESS_TEMPLATE.format(
                command=command, stdout=stdout_decoded
            )
        else:
            stdout_decoded = stdout.decode().strip()
            stderr_decoded = stderr.decode().strip()
            return True, ERROR_TEMPLATE.format(
                command=command,
                code=code,
                stdout=stdout_decoded,
                stderr=stderr_decoded,
            )
