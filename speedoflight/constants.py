APPLICATION_ID = "io.speedoflight.App"
APPLICATION_NAME = "Speed of Light"

CONFIG_FILE = "config.toml"
LOG_FILE = "speedoflight.log"

DEFAULT_SPACING = 10
DEFAULT_MARGIN = 10

# Agent Service Signals
AGENT_UPDATE_AI_SIGNAL = "agent-update-ai"
AGENT_UPDATE_TOOL_SIGNAL = "agent-update-tool"
AGENT_UPDATE_SOL_SIGNAL = "agent-update-sol"
AGENT_READY_SIGNAL = "agent-ready"
AGENT_RUN_STARTED_SIGNAL = "agent-run-started"
AGENT_RUN_COMPLETED_SIGNAL = "agent-run-completed"

# MCP Service Signals
SERVER_INITIALIZED_SIGNAL = "server-initialized"

# UI Signals
SEND_MESSAGE_SIGNAL = "send-message"

# Desktop tool names
TOOL_CLIPBOARD_GET_NAME = "clipboard_get"
TOOL_CLIPBOARD_SET_NAME = "clipboard_set"

# Anthropic tool names (reuse for other LLMs)
TOOL_WEB_SEARCH_NAME = "web_search"
TOOL_COMPUTER_USE_NAME = "computer"

# Recommendation is to keep display resolution at or below 1280x800 (WXGA)
# for best performance. If the image's long edge is more than 1568 pixels,
# it will first be scaled down. See:
# https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/computer-use-tool#tool-parameters
# https://docs.anthropic.com/en/docs/build-with-claude/vision#evaluate-image-size
MAX_IMAGE_SIZE = 1280

# Image format for screenshot output
PNG_FORMAT = "png"
