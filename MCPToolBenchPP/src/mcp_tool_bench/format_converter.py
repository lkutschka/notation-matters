import json
import uuid
import logging
import re
from typing import Any, Dict, List, Optional
from enum import Enum

import shared_format


class ToolFormat(str, Enum):
    JSON = "json"
    TOON = "toon"
    TRON = "tron"


class ToolMode(str, Enum):
    API = "api"
    PROMPT = "prompt"


class ToolFormatConverter:
    """
    Converts data between Python dicts and a target serialization format (JSON/TOON/TRON).
    Also handles prompt-mode tool calling: building system prompts with tool definitions
    and parsing tool calls from LLM free-text responses.
    """

    def __init__(self, format: ToolFormat = ToolFormat.JSON, mode: ToolMode = ToolMode.API,
                 tool_call_format: Optional[ToolFormat] = None):
        self.format = format
        self.mode = mode
        # Format for LLM tool call output; defaults to main format
        self.tool_call_format = tool_call_format if tool_call_format is not None else format
        # Per-converter format-violation counter; surfaced in run_info so the
        # paper can show format-violation rate across formats × models.
        self.format_violations = 0

    def is_prompt_mode(self) -> bool:
        return self.mode == ToolMode.PROMPT

    def _shared_fmt(self) -> shared_format.ToolFormat:
        """Map local ToolFormat to shared_format.ToolFormat."""
        fmt_val = self.format.value if isinstance(self.format, ToolFormat) else str(self.format)
        return shared_format.ToolFormat(fmt_val)

    def serialize(self, data: Any) -> str:
        """Convert a Python dict/list/value to the target format string."""
        return shared_format.serialize(data, self._shared_fmt())

    def deserialize(self, text: str) -> Any:
        """Parse a format string back to Python dict/list/value."""
        return shared_format.deserialize(text, self._shared_fmt())

    def deserialize_lenient(self, text: str) -> Any:
        """Try target format first, fall back to JSON."""
        return shared_format.deserialize_lenient(text, self._shared_fmt())

    def _get_format_explanation(self) -> str:
        """Return a brief explanation of the target format syntax."""
        return shared_format.get_format_explanation(self._shared_fmt())

    def _shared_tc_fmt(self) -> shared_format.ToolFormat:
        """Map local tool_call_format to shared_format.ToolFormat."""
        fmt_val = self.tool_call_format.value if isinstance(self.tool_call_format, ToolFormat) else str(self.tool_call_format)
        return shared_format.ToolFormat(fmt_val)

    def build_tool_call_system_prompt(self, tools: List[Dict]) -> str:
        """
        Build a system prompt for prompt-mode tool calling.
        Tool definitions use self.format (input format).
        Tool call instructions/examples use self.tool_call_format (output format).
        """
        input_fmt = self._shared_fmt()
        output_fmt = self._shared_tc_fmt()
        input_name = shared_format.get_format_name(input_fmt)
        output_name = shared_format.get_format_name(output_fmt)

        # Format intro explains the input format used for tool definitions
        format_intro = shared_format.get_format_intro(input_fmt)

        # If output format differs, add explanation for it too
        output_intro = ""
        if input_fmt != output_fmt:
            output_intro = f"\n\nFor your tool call responses, use {output_name} format.\n{shared_format.get_format_explanation(output_fmt)}"

        output_reminder = shared_format.get_format_reminder(output_fmt)

        # Serialize tool definitions in input format
        tool_defs = []
        for tool in tools:
            tool_defs.append({
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {})
            })
        tools_block = shared_format.serialize_tools(tool_defs, input_fmt)

        # Build example tool call in output format
        example_call = shared_format.serialize_example({
            "name": "example_tool",
            "arguments": {"param1": "value1", "param2": "value2"}
        }, output_fmt)

        return f"""You are a helpful assistant with access to tools.

{format_intro}{output_intro}

Below are the available tools in {input_name} format:

{tools_block}

When you need to call a tool, output the marker TOOL_CALL on its own line (in plain text, NOT inside a code block or JSON object), followed by the tool call in {output_name} format with keys "name" (the tool name) and "arguments" (an object with the parameters):

TOOL_CALL
{example_call}

RULES:
- Output ONLY ONE tool call per response
- The block AFTER TOOL_CALL must be valid {output_name}; the TOOL_CALL marker itself is plain text and must NOT be wrapped in a code fence or JSON object.
- If no tool is needed, respond normally WITHOUT the TOOL_CALL marker
- Do NOT include any text before TOOL_CALL when calling a tool"""

    def _extract_json_object(self, text: str) -> Optional[str]:
        """Extract the first complete JSON object from text by matching balanced braces."""
        start = text.find('{')
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == '\\' and in_string:
                escape = True
                continue
            if c == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
        return None

    def parse_tool_call_from_text(self, text: str) -> Dict:
        """
        Parse a tool call from LLM free-text response.
        Looks for the TOOL_CALL marker and deserializes the entire tool call
        structure from the target format.

        Returns standardized format matching function_call_result_common_mapper output:
        {
            "function_name": str,
            "function_arguments": str (JSON string for compatibility),
            "is_function_call": bool,
            "id": str
        }
        """
        if not text or "TOOL_CALL" not in text:
            return {}

        try:
            # Find TOOL_CALL marker and get everything after it
            marker_idx = text.index("TOOL_CALL")
            after_marker = text[marker_idx + len("TOOL_CALL"):].strip()

            # Try to deserialize the entire tool call structure from target format
            tool_call = None

            tc_fmt = self.tool_call_format
            strict_succeeded = False
            tron_class_violation = False
            raw_for_class_check = after_marker
            if tc_fmt == ToolFormat.JSON or tc_fmt == ToolFormat.TRON:
                # For JSON/TRON, extract balanced {} first to avoid trailing text
                json_str = self._extract_json_object(after_marker)
                if json_str:
                    try:
                        tool_call = shared_format.deserialize_strict(json_str, self._shared_tc_fmt())
                        strict_succeeded = True
                    except shared_format.FormatViolation:
                        # Try plain JSON as a backstop (TRON is JSON-superset);
                        # do NOT count as success if this needs to fall back.
                        try:
                            tool_call = json.loads(json_str)
                        except Exception:
                            pass
            elif tc_fmt == ToolFormat.TOON:
                # For TOON, the indented block after TOOL_CALL is the tool call
                # Strip any trailing non-TOON text (e.g. LLM explanation after blank line)
                toon_text = after_marker
                blank_line = re.search(r'\n\s*\n', toon_text)
                if blank_line:
                    toon_text = toon_text[:blank_line.start()]
                try:
                    tool_call = shared_format.deserialize_strict(toon_text.strip(), self._shared_tc_fmt())
                    strict_succeeded = True
                except shared_format.FormatViolation:
                    pass

            # TRON-specific: emitting plain JSON for 2+ same-shape objects skips
            # TRON's compression feature. Count as format violation.
            if tc_fmt == ToolFormat.TRON and tool_call is not None and \
                    not shared_format.tron_uses_class_when_possible(raw_for_class_check, tool_call):
                tron_class_violation = True

            # Fallback: try the old name:/arguments: regex approach
            if not tool_call or not isinstance(tool_call, dict) or "name" not in tool_call:
                tool_call = self._parse_tool_call_regex_fallback(after_marker)
                # Reaching here means strict parse FAILED — count it
                self.format_violations += 1
            elif not strict_succeeded:
                # We got a tool_call but only via the JSON backstop, not strict
                self.format_violations += 1
            elif tron_class_violation:
                self.format_violations += 1

            if not tool_call or not isinstance(tool_call, dict) or "name" not in tool_call:
                logging.error(f"Could not parse tool call from text after TOOL_CALL marker")
                return {}

            tool_name = tool_call.get("name", "")
            args_dict = tool_call.get("arguments", {})
            # TOON gotcha: `arguments: {}` parses as the string '{}'. Coerce
            # obvious-empty literals to a real empty dict.
            args_dict = shared_format.coerce_empty_inline_literal(args_dict)
            if not isinstance(args_dict, dict):
                args_dict = {}

            logging.debug(f"Parsed tool call: name={tool_name}, args={args_dict}")

            return {
                "function_name": tool_name,
                "function_arguments": json.dumps(args_dict),
                "is_function_call": True,
                "id": f"prompt-{uuid.uuid4().hex[:12]}"
            }
        except Exception as e:
            logging.error(f"Failed to parse tool call from text: {e}")
            return {}

    def _parse_tool_call_regex_fallback(self, after_marker: str) -> Optional[Dict]:
        """Fallback parser using regex for name: / arguments: pattern."""
        name_match = re.search(r'name:\s*(.+)', after_marker)
        if not name_match:
            return None
        tool_name = name_match.group(1).strip()

        args_match = re.search(r'arguments:\s*\n?([\s\S]*)', after_marker)
        if not args_match:
            return {"name": tool_name, "arguments": {}}

        args_text = args_match.group(1).strip()
        # Try extracting JSON object
        json_str = self._extract_json_object(args_text)
        if json_str:
            try:
                return {"name": tool_name, "arguments": json.loads(json_str)}
            except Exception:
                pass
        # Try target format deserialization
        try:
            args_dict = self.deserialize(args_text)
            if isinstance(args_dict, dict):
                return {"name": tool_name, "arguments": args_dict}
        except Exception:
            pass
        return {"name": tool_name, "arguments": {}}


# Module-level singleton
_global_format_converter = ToolFormatConverter(ToolFormat.JSON, ToolMode.API)


def get_format_converter() -> ToolFormatConverter:
    return _global_format_converter


def set_format_converter(format_str: str, mode_str: str, tool_call_format_str: str = None):
    global _global_format_converter
    format_enum = ToolFormat(format_str.lower())
    mode_enum = ToolMode(mode_str.lower())
    tc_enum = ToolFormat(tool_call_format_str.lower()) if tool_call_format_str else None
    _global_format_converter = ToolFormatConverter(format_enum, mode_enum, tool_call_format=tc_enum)
