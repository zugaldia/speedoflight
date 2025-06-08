# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Commands
```bash
make lint       # Run ruff linter on speedoflight/
make typecheck  # Run mypy type checker on speedoflight/
```

## Code Style
- Use type annotation whenever possible
- Do not add comments for obvious behavior
- When comments are recommended, keep them short

## Architecture Overview

Speed of Light is a GTK4-based desktop AI agent application with a service-oriented architecture.

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