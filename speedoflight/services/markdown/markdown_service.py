"""

Originally, we implemented this service with PyPandoc, which is the same
library that the GNOME Apostrophe uses. However, it needs the pandoc command
to be installed on the system, while mistune doesn't come with any system
dependencies.

"""

import mistune

from speedoflight.services.base_service import BaseService


class MarkdownService(BaseService):
    def __init__(self):
        super().__init__(service_name="markdown")
        self._markdown = mistune.create_markdown()
        self._logger.info("Initialized.")

    def markdown_to_pango(self, markdown_text: str) -> str:
        try:
            result = self._markdown(markdown_text)
            # The result could be a list with the Abstract Syntax Tree (AST)
            # if we wanted, by setting renderer=None (which we are not).
            return result if isinstance(result, str) else markdown_text
        except Exception as e:
            self._logger.error(f"Error converting markdown to HTML: {e}")
            return markdown_text

    def shutdown(self):
        self._logger.info("Shutting down.")
