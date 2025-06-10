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
- It has service-oriented architecture developed with Python.
- The UI follows the Model-View-ViewModel (MVVM) pattern.

### Core Services Pattern
All services inherit from `BaseService` (base_service.py) which provides:
- GObject-based signal support for event-driven communication
- Lifecycle management (init/shutdown)

### Service Hierarchy
1. **ConfigurationService**: Manages app configuration (model selection, MCP servers)
2. **AgentService**: Handles LangChain/LangGraph agent execution with async operations
3. **OrchestratorService**: Coordinates between UI and agent, manages user sessions

### UI Framework
- GTK4 with Adwaita design system (dark mode only)
- PyGObject bindings for Python
- Custom styling via `speedoflight/data/style.css`
- Main window components in `speedoflight/ui/main/`

### Agent Architecture
- Uses LangGraph ReAct agent with in-memory checkpointing
- Supports multiple LLM providers via LangChain's `init_chat_model`
- Extensible via Model Context Protocol (MCP) servers
- Message types: HumanMessage, AIMessage, ToolMessage

### Configuration
Configuration is managed via `config.json`:
- `model`: LLM model in format `provider:model_name` (default: `ollama:llama3.2`)
- `mcp_servers`: Dictionary of MCP server configurations

The app creates a default config if none exists, using local Ollama with Llama 3.2.