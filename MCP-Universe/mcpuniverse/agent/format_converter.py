"""
Serialization format converter for tool descriptions and agent responses.
Supports JSON, TOON, and TRON formats.
Adapted from MCPToolBenchPP's format_converter.py for MCP-Universe's architecture.
Delegates core serialization to shared_format for cross-benchmark consistency.
"""
import logging
from typing import Any, Dict, List
from enum import Enum

import shared_format


class ToolFormat(str, Enum):
    JSON = "json"
    TOON = "toon"
    TRON = "tron"


class ToolFormatConverter:
    """
    Converts data between Python dicts and a target serialization format.
    Each agent creates its own instance from config.
    """

    def __init__(self, format: ToolFormat = ToolFormat.JSON,
                 tool_call_format: ToolFormat = None):
        self.format = format
        # Format for LLM tool call output; defaults to main format
        self.tool_call_format = tool_call_format if tool_call_format is not None else format

    def _shared_fmt(self) -> shared_format.ToolFormat:
        """Map local format to shared_format.ToolFormat."""
        fmt_val = self.format.value if isinstance(self.format, ToolFormat) else str(self.format)
        return shared_format.ToolFormat(fmt_val)

    def _shared_tc_fmt(self) -> shared_format.ToolFormat:
        """Map local tool_call_format to shared_format.ToolFormat."""
        fmt_val = self.tool_call_format.value if isinstance(self.tool_call_format, ToolFormat) else str(self.tool_call_format)
        return shared_format.ToolFormat(fmt_val)

    def serialize(self, data: Any) -> str:
        """Convert a Python dict/list/value to the target format string."""
        return shared_format.serialize(data, self._shared_fmt())

    def deserialize(self, text: str) -> Any:
        """Parse a format string back to Python dict/list/value."""
        return shared_format.deserialize(text, self._shared_fmt())

    def deserialize_lenient(self, text: str) -> Any:
        """Try target format first, fall back to JSON, fall back to {}."""
        return shared_format.deserialize_lenient(text, self._shared_fmt())

    def get_format_name(self) -> str:
        """Return the uppercase format name for prompt inclusion."""
        return shared_format.get_format_name(self._shared_fmt())

    def get_format_explanation(self) -> str:
        """Return a brief explanation of the target format syntax."""
        return shared_format.get_format_explanation(self._shared_fmt())

    def serialize_tools(self, tools: Dict[str, List[Any]]) -> str:
        """
        Serialize all MCP tools to the target format.

        Args:
            tools: Dict[server_name, List[Tool]] — MCP tool objects with
                   .name, .description, .inputSchema attributes.

        Returns:
            Formatted string of all tool definitions separated by '---'.
        """
        return shared_format.serialize_tools(tools, self._shared_fmt())

    def get_tool_call_format_name(self) -> str:
        """Return the uppercase tool call format name."""
        return shared_format.get_format_name(self._shared_tc_fmt())

    def get_tool_call_format_explanation(self) -> str:
        """Return explanation of the tool call output format."""
        return shared_format.get_format_explanation(self._shared_tc_fmt())

    def serialize_response_example(self, action: bool = True) -> str:
        """
        Generate an example response structure in the tool call output format.

        Args:
            action: If True, generate a tool-call example. If False, a final-answer example.
        """
        if action:
            example = {
                "thought": "Your detailed reasoning about what to do next",
                "action": {
                    "reason": "Explanation of why you chose this tool",
                    "server": "server-name",
                    "tool": "tool-name",
                    "arguments": {"argument-name": "argument-value"},
                },
            }
        else:
            example = {
                "thought": "Your final reasoning process to derive the answer.",
                "answer": "Final answer to the query",
            }
        return shared_format.serialize_example(example, self._shared_tc_fmt())
