# Anthropic does this automatically.
# See:
# https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use#tool-use-system-prompt
TOOL_USE_PROMPT = """
In this environment you have access to a set of tools you can use to answer the user's question.
{{ FORMATTING INSTRUCTIONS }}
String and scalar parameters should be specified as is, while lists and objects should use JSON format.
Note that spaces for string values are not stripped.
The output is not expected to be valid XML and is parsed with regular expressions.
Here are the functions available in JSONSchema format:
{{ TOOL DEFINITIONS IN JSON SCHEMA }}
{{ USER SYSTEM PROMPT }}
{{ TOOL CONFIGURATION }}
""".strip()


# See:
# https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview#chain-of-thought-tool-use

CHAIN_OF_THOUGHT_PROMPT = """
Answer the user's request using relevant tools (if they are available).
Before calling a tool, do some analysis within \<thinking>\</thinking> tags.
First, think about which of the provided tools is the relevant tool to answer the user's request.
Second, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value.
When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value.
If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool call.
BUT, if one of the values for a required parameter is missing, DO NOT invoke the function (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters.
DO NOT ask for more information on optional parameters if it is not provided.
""".strip()
