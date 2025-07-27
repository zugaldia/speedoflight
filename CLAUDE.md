# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Commands
You should run both after making changes to the codebase (also checked by CI):

```bash
make lint         # Run ruff linter on speedoflight/
make format-check # Run ruff format check on speedoflight/
```

## Code Style
- Use type annotation whenever possible
- Do not add comments for obvious behavior
- When comments are recommended, keep them short
- Avoid relative imports, always use absolute imports

## Architecture Overview
- Speed of Light is a GTK4-based Linux desktop application
- It has service-oriented architecture developed with Python
- The UI follows the Model-View-ViewModel (MVVM) pattern

### Core Services Pattern
All services inherit from `BaseService` (base_service.py) which provides:
- GObject-based signal support for event-driven communication
- Lifecycle management (init/shutdown)

### Service Hierarchy
1. **ConfigurationService**: Manages app configuration (model selection, MCP servers)
2. **OrchestratorService**: Coordinates between UI and agent, manages user sessions
3. **AgentService**: Handles MCP and LLM execution with async operations
4. **LlmService**: Manages LLM provider selection and native SDK integration
5. **McpService**: Manages MCP server connections and tool execution

### UI Framework
- GTK4 with Adwaita design system (dark mode only)
- PyGObject bindings for Python
- Custom styling via `speedoflight/data/style.css`
- Main window components in `speedoflight/ui/main/`
- Chat messages rendered using GtkSourceView with markdown syntax highlighting

### MVVM Pattern Implementation
- **ViewModels**: Inherit from `BaseViewModel` (base_view_model.py) with GObject support and logging
- **ViewStates**: Inherit from `BaseViewState` (base_view_state.py) for data binding
- All UI components follow GObject signal-based communication

### Key Dependencies
- **MCP**: Official Model Context Protocol (MCP) Python SDK
- **PyGObject**: GTK4 Python bindings
- **Native LLM SDKs**: Direct integration with provider SDKs
  - Anthropic SDK for Claude models
  - Ollama SDK for local models
  - Additional providers can be added by implementing `BaseLlmService`

### Threading & Signals
- Services use asyncio with a GLibEventLoopPolicy to avoid blocking UI
- Use `BaseService.safe_emit()` to emit signals from threads (wraps with GLib.idle_add)
- All signal emissions must be thread-safe for main GTK loop

### Agent Architecture
- Supports multiple LLM providers using their native SDKs
- Extensible via Model Context Protocol (MCP) servers
- Clean abstraction layers:
  - `BaseLlmService`: Interface for LLM providers
  - `BaseServer`: Interface for MCP server types (stdio, HTTP)

### Configuration
Configuration is managed via `config.toml` (TOML format):
- `llm`: LLM provider selection (e.g., "ollama", "anthropic")
- `[llms.<provider>]`: Provider-specific configuration sections
- `[mcps.<server>]`: MCP server configurations

The app creates a default config if none exists, using local Ollama.
