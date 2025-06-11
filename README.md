# Speed of Light

Speed of Light (SOL) is a native AI Agent for the Linux desktop.
You can extend its functionality with tools, including MCP tools:
<div align="center">
  <img src="assets/sol-mapbox.png" alt="SOL Screenshot">
  <br><em>Example of SOL running the Mapbox MCP server.</em>
</div>

## Features
- 🏠 Support for both local (default) and cloud providers.
- 🔧 Extensible via [Model Context Protocol](https://modelcontextprotocol.io) (MCP) servers.
- 🐧 Built-in tools that integrate with the Linux desktop (e.g., clipboard access).
- 🎨 Developed with GNOME Adwaita for a modern look and compatibility with any desktop environment.

## Launch the app

Clone this repo, install the dependencies in a virtual environment, and launch the app with Python:

```bash
$ git clone git@github.com:zugaldia/speedoflight.git
$ cd speedoflight
$ python3 -m venv venv
$ source venv/bin/activate
$ pip3 install -r requirements.txt
$ python3 launch.py
```

## Configure the app

SOL uses a `config.json` file for configuration. On first run, if no configuration file exists, SOL will create a default one. You can also create your own by copying the example:

```bash
$ cp config.example.json config.json
```

The configuration file has the following structure:

```json
{
  "model": "ollama:llama3.2",
  "mcp_servers": {},
  "cloud_tools": {},
  "agent_debug": false
}
```

### Configuration Options

- **`model`**: The LLM model to use. Format is `provider:model_name`. Examples:
  - `ollama:llama3.2` (default - requires local Ollama installation)
  - `anthropic:claude-sonnet-4-20250514` or `anthropic:claude-opus-4-20250514` (requires `ANTHROPIC_API_KEY` environment variable)
  - `google_genai:gemini-2.5-flash-preview-05-20` or `google_genai:gemini-2.5-pro-preview-06-05` (requires `GOOGLE_API_KEY` environment variable)
  - `openai:gpt-4.1` (requires `OPENAI_API_KEY` environment variable)

- **`agent_debug`**: Enables debug mode in the agent (default: `false`). When enabled, more detailed information will be logged to the terminal, which is useful for troubleshooting.

- **`mcp_servers`**: Configuration for MCP servers. This allows extending the agent with additional tools. For example, to add the [Mapbox MCP](https://github.com/mapbox/mcp-server) so that SOL can search for places and create maps, you would add the following:

```json
{
  "mcp_servers": {
    "mapbox": {
      "transport": "stdio",
      "command": "node",
      "args": ["/path/to/mcp-server/dist/index.js"],
      "env": {"MAPBOX_ACCESS_TOKEN": "[YOUR_MAPBOX_ACCESS_TOKEN_GOES_HERE]"}
    }
  }
}
```

Note that MCP servers are optional. SOL works with no servers configured (`"mcp_servers": {}`), in which case you would be talking to the LLM directly without any additional tools.

- **`cloud_tools`**: Configuration for cloud-based tools that are executed by the LLM provider. These are pre-built tools that don't require local implementation. The configuration varies slightly between providers:

```json
{
  "cloud_tools": {
    "anthropic:claude-opus-4-20250514": [
      {
        "type": "web_search_20250305",
        "name": "web_search"
      }
    ],
    "google_genai:gemini-2.5-flash-preview-05-20": [
      {
        "name": "google_search"
      }
    ],
    "openai:gpt-4.1": [
      {
        "type": "web_search_preview"
      }
    ]
  }
}
```

Each model can have its own set of cloud tools. When cloud tools are used, SOL will display a visual indication in the chat interface.

## Extending the app

To extend SOL's capabilities, you need to make more "tools" available to it. In the current context of LLMs, tools can have different origins and implementations, described below.

We currently support:

- **MCP tools**: This is the primary mechanism to extend the tools available to SOL by a user. MCP is a provider agnostic standard which enables integrating with third-party providers and on-device functionality.

- **Built-in tools**: These are tools defined and implemented by SOL and available together with the other tools above. For example, we include two tools that allow SOL to read and send the clipboard content. One possibility is to eventually graduate these built-in tools as their own MCP servers to simplify SOL's architecture and make these tools available to any MCP client.

- **Cloud tools**: These are pre-built tools that are provider-specific and executed on the provider's server. They are configured per model in the `cloud_tools` section and don't require local implementation. Examples include web search tools available from providers like Google, Anthropic, and OpenAI.

We currently do not support, but plan to:

- **Computer use**: These are also tools that are to some extent provider-specific ([example](https://platform.openai.com/docs/guides/tools-computer-use)), but they do require implementation on SOL's side.

## Reporting Issues

If you encounter any bugs, have feature requests, or need help with Speed of Light, please open an issue on our GitHub repository:

**[Report an Issue](https://github.com/zugaldia/speedoflight/issues)**

When reporting issues, please include:
- Your operating system and version
- The model and configuration you're using
- Steps to reproduce the issue
- Any relevant error messages or logs

It's also helpful to tag your issues appropriately. In addition to standard GitHub labels, we have specific tags for providers (`provider_anthropic`, `provider_google`, `provider_ollama`, `provider_openai`) and tool types (`tools_builtin`, `tools_cloud`, `tools_computer_use`, `tools_mcp`) to help us categorize and prioritize issues effectively. 
