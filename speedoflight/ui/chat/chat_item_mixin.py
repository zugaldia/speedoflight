import logging
from typing import Union

from langchain_core.messages import BaseMessage

from speedoflight.utils import is_empty


class ChatItemMixin:
    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def extract_text(self, message: BaseMessage) -> list[str]:
        content: Union[str, list[Union[str, dict]]] = message.content
        if isinstance(content, str):
            return [content] if not is_empty(content) else []

        lines = []
        for item in content:
            if isinstance(item, str):
                if not is_empty(item):
                    lines.append(item)
            elif isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    text = item["text"]
                    if not is_empty(text):
                        lines.append(text)
                elif item.get("type") == "tool_use":
                    pass  # We handle tool use info separately, so skip here
                else:
                    item_type = item.get("type")
                    self._logger.info(f"Type {item_type} not currently supported.")
        return lines

    def extract_artifacts(self, message: BaseMessage) -> list:
        if not hasattr(message, "artifact") or not message.artifact:
            return []

        artifacts = (
            message.artifact
            if isinstance(message.artifact, list)
            else [message.artifact]
        )

        supported_artifacts = []
        for artifact in artifacts:
            if artifact.get("type") == "image":
                supported_artifacts.append(artifact)
            else:
                artifact_type = artifact.get("type", "unknown")
                self._logger.warning(f"Artifact {artifact_type} not supported.")

        return supported_artifacts
