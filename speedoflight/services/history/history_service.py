from datetime import datetime
from pathlib import Path

from speedoflight.models import BaseMessage
from speedoflight.services.base_service import BaseService
from speedoflight.utils import get_data_path


class HistoryService(BaseService):
    def __init__(self):
        super().__init__(service_name="history")

        # TODO: This is a naive implementation. We should probably create a
        # memory service where we track tokens limits and summarize old
        # history as needed.
        self._messages: list[BaseMessage] = []
        self._session_id: str | None = None
        self._session_dir: Path | None = None
        self._messages_file: Path | None = None
        self._directory_created: bool = False
        self._logger.info("Initialized.")

    def set_session_id(self, session_id: str):
        """Set the session ID for this history service."""
        self._session_id = session_id
        self._messages = []

        # Set up paths but don't create directories yet
        date_folder = datetime.now().strftime("%Y%m%d")
        self._session_dir = get_data_path() / "sessions" / date_folder / session_id
        self._messages_file = self._session_dir / "messages.jsonl"
        self._directory_created = False
        self._logger.info(f"Messages cleared, session ID set to: {session_id}")

    def add_message(self, message: BaseMessage):
        """Add a message to the conversation history."""
        self._messages.append(message)

        encoded = message.model_dump_json()
        self._store_messages(encoded)

        total_messages = len(self._messages)
        self._logger.info(
            f"Added {message.role} message (total: {total_messages}): {message.id}"
        )

    def _ensure_session_directory(self):
        """Create session directory structure if not already created."""
        if self._directory_created or not self._session_dir:
            return

        try:
            self._session_dir.mkdir(parents=True, exist_ok=True)
            self._directory_created = True
            self._logger.info(f"Session directory created: {self._session_dir}")
        except Exception as e:
            self._logger.error(
                f"Failed to create session directory {self._session_dir}: {e}"
            )

    def _store_messages(self, encoded: str):
        if not self._messages_file:
            return

        try:
            self._ensure_session_directory()
            with open(self._messages_file, "a", encoding="utf-8") as f:
                f.write(encoded + "\n")
        except Exception as e:
            self._logger.error(f"Failed to write message to {self._messages_file}: {e}")

    @property
    def messages(self) -> list[BaseMessage]:
        """Get the current message history."""
        return self._messages

    def shutdown(self):
        pass
