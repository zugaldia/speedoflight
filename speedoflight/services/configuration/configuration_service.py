import os
from typing import Optional

from speedoflight.models import AppConfig
from speedoflight.services.base_service import BaseService


class ConfigurationService(BaseService):
    CONFIG_FILE_PATH = "config.json"

    def __init__(self):
        super().__init__(service_name="configuration")
        self._config: Optional[AppConfig] = None
        self._logger.info("Initialized.")

    def get_config(self) -> AppConfig:
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> AppConfig:
        if not os.path.exists(self.CONFIG_FILE_PATH):
            self._logger.info(f"Creating default {self.CONFIG_FILE_PATH}.")
            return self._create_default_config()

        try:
            with open(self.CONFIG_FILE_PATH, "r") as f:
                json_content = f.read()
            config = AppConfig.model_validate_json(json_content)
            self._logger.info(f"Configuration loaded from {self.CONFIG_FILE_PATH}")
            return config
        except Exception as e:
            raise Exception(f"Failed to load {self.CONFIG_FILE_PATH}: {str(e)}")

    def _create_default_config(self) -> AppConfig:
        try:
            default_config = AppConfig()
            json_content = default_config.model_dump_json(indent=2)
            with open(self.CONFIG_FILE_PATH, "w") as f:
                f.write(json_content)
            self._logger.info(f"Default {self.CONFIG_FILE_PATH} created.")
            return default_config
        except Exception as e:
            raise Exception(f"Failed to create {self.CONFIG_FILE_PATH}: {str(e)}")

    def shutdown(self):
        self._logger.info("Shutting down.")
