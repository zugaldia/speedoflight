from speedoflight.services.desktop.command_service import CommandService

YDOTOOL = "/usr/bin/ydotool"


class YdotoolService(CommandService):
    def __init__(self):
        super().__init__(service_name="ydotool")
        self._logger.info("Initialized.")
