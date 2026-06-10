"""
A ReAct agent implementation.

This module contains the ReAct agent class and its configuration, based on the paper
'ReAct: Synergizing Reasoning and Acting in Language Models' (https://arxiv.org/abs/2210.03629).
"""
# pylint: disable=broad-exception-caught
import os
import re
import json
from typing import Optional, Union, Dict, List
from collections import OrderedDict
from dataclasses import dataclass
from mcp.types import TextContent

from mcpuniverse.mcp.manager import MCPManager
from mcpuniverse.llm.base import BaseLLM
from mcpuniverse.common.logger import get_logger
from mcpuniverse.tracer import Tracer
from mcpuniverse.utils.token_counter import count_tokens
import shared_format
from mcpuniverse.agent.format_converter import ToolFormatConverter, ToolFormat
from mcpuniverse.callbacks.base import (
    send_message,
    send_message_async,
    CallbackMessage,
    MessageType
)
from .base import BaseAgentConfig, BaseAgent
from .utils import build_system_prompt
from .types import AgentResponse

DEFAULT_CONFIG_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "configs")


@dataclass
class ReActConfig(BaseAgentConfig):
    """
    Configuration class for ReAct agents.

    Attributes:
        system_prompt (str): The system prompt template file or string.
        context_examples (str): Additional context examples for the agent.
        max_iterations (int): Maximum number of reasoning iterations.
        summarize_tool_response (bool): Whether to summarize tool responses using the LLM.
    """
    system_prompt: str = os.path.join(DEFAULT_CONFIG_FOLDER, "react_prompt.j2")
    context_examples: str = ""
    max_iterations: int = 5
    summarize_tool_response: bool = False


class ReAct(BaseAgent):
    """
    ReAct agent implementation.

    This class implements the ReAct (Reasoning+Acting) paradigm,
    allowing the agent to alternate between reasoning and acting to solve tasks.

    Attributes:
        config_class (Type[ReActConfig]): The configuration class for this agent.
        alias (List[str]): Alternative names for this agent type.
    """
    config_class = ReActConfig
    alias = ["react"]

    def __init__(
            self,
            mcp_manager: MCPManager,
            llm: BaseLLM,
            config: Optional[Union[Dict, str]] = None
    ):
        """
        Initialize a ReAct agent.

        Args:
            mcp_manager (MCPManager): An MCP server manager for handling tool interactions.
            llm (BaseLLM): A language model for generating responses.
            config (Optional[Union[Dict, str]]): Agent configuration as a dictionary or file path.
        """
        super().__init__(mcp_manager=mcp_manager, llm=llm, config=config)
        self._logger = get_logger(f"{self.__class__.__name__}:{self._name}")
        self._history: List[str] = []
        tc_fmt = self._config.tool_call_format or self._config.tool_format
        self._format_converter = ToolFormatConverter(
            format=ToolFormat(self._config.tool_format),
            tool_call_format=ToolFormat(tc_fmt)
        )

    def _build_prompt(self, question: str):
        """
        Construct the prompt for the language model.

        Args:
            question (str): The user's question or task.

        Returns:
            str: The constructed prompt including system instructions, context, and history.
        """
        fc = self._format_converter
        is_non_json = fc.format != ToolFormat.JSON or fc.tool_call_format != ToolFormat.JSON

        params = {
            "INSTRUCTION": self._config.instruction,
            "QUESTION": question,
            "MAX_STEPS": self._config.max_iterations
        }
        if self._config.context_examples:
            params.update({"CONTEXT_EXAMPLES": self._config.context_examples})
        params.update(self._config.template_vars)
        if self._history:
            params.update({"HISTORY": "\n\n".join(self._history)})

        if is_non_json:
            # Use format-aware template with pre-serialized tool descriptions
            template_path = os.path.join(DEFAULT_CONFIG_FOLDER, "react_prompt_format.j2")
            # Input format for tool definitions
            input_name = fc.get_format_name()
            input_explanation = fc.get_format_explanation()
            # Output format for LLM responses (may differ)
            output_name = fc.get_tool_call_format_name()
            output_explanation = fc.get_tool_call_format_explanation()

            format_name = input_name
            format_explanation = input_explanation
            # If output differs from input, append output format info
            if fc.format != fc.tool_call_format:
                format_explanation += f"\n\nFor your responses, use {output_name} format:\n{output_explanation}"
                format_name = f"{input_name} (input) / {output_name} (output)"

            params.update({
                "FORMAT_NAME": format_name,
                "FORMAT_EXPLANATION": format_explanation,
                "FORMAT_TOOLS_DESCRIPTION": fc.serialize_tools(self._tools),
                "FORMAT_ACTION_EXAMPLE": fc.serialize_response_example(action=True),
                "FORMAT_ANSWER_EXAMPLE": fc.serialize_response_example(action=False),
            })
            return build_system_prompt(
                system_prompt_template=template_path,
                tool_prompt_template="",
                tools=None,
                format_converter=fc,
                **params
            )

        return build_system_prompt(
            system_prompt_template=self._config.system_prompt,
            tool_prompt_template=self._config.tools_prompt,
            tools=self._tools,
            format_converter=fc,
            **params
        )

    def _add_history(self, history_type: str, message: str):
        """
        Add a record to the agent's conversation history.

        Args:
            history_type (str): The type of the history entry (e.g., "thought", "action", "result").
            message (str): The content of the history entry.
        """
        self._history.append(f"{history_type.title()}: {message}")

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Strip markdown code fences AND <think>...</think> blocks from response.

        Reasoning models (Qwen3, DeepSeek-R1) emit `<think>...</think>` before
        the actual structured response. Llama-4 wraps the JSON object inside a
        ```json … ``` fence after a markdown `## Thought:` / `## Action:` header.
        Without these strips the strict-deserialize sees prose first and rejects
        the whole document as a format violation.
        """
        text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = text.strip()
        # If the response contains a fenced block, extract its contents — strip
        # any leading prose / markdown headers before the fence (Llama-4 style).
        fenced = re.search(
            r"```(?:json|toon|tron)?\s*\n(.*?)\n```",
            text,
            flags=re.DOTALL,
        )
        if fenced:
            return fenced.group(1).strip()
        # Fall back: remove a leading/trailing fence (any position-anchored form)
        text = re.sub(r'^```(?:json|toon|tron)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
        return text.strip()

    async def _execute(
            self,
            message: Union[str, List[str]],
            output_format: Optional[Union[str, Dict]] = None,
            **kwargs
    ) -> AgentResponse:
        """
        Execute the ReAct agent's reasoning and action loop.

        This method processes the user's message, generates thoughts and actions,
        and returns a final answer or explanation.

        Args:
            message (Union[str, List[str]]): The user's message or a list of messages.
            output_format (Optional[Union[str, Dict]]): Desired format for the output.
            **kwargs: Additional keyword arguments.

        Returns:
            AgentResponse: The agent's final response, including the answer and trace information.
        """
        if isinstance(message, (list, tuple)):
            message = "\n".join(message)
        if output_format is not None:
            message = message + "\n\n" + self._get_output_format_prompt(output_format)
        tracer = kwargs.get("tracer", Tracer())
        callbacks = kwargs.get("callbacks", [])
        fc = self._format_converter

        # Local token counting accumulators
        local_token_counts = {
            "mcp_schema_tokens": 0,
            "tool_call_output_tokens": 0,
            "tool_result_tokens": 0,
        }
        # Count steps where the LLM emitted output that didn't parse as the
        # configured tool_call_format. Surfaced via tracer + the agent return
        # so the per-task report can show format-violation rate.
        format_violations = 0

        for iter_num in range(self._config.max_iterations):
            prompt = self._build_prompt(message)

            # Count MCP schema tokens on first iteration
            if iter_num == 0:
                local_token_counts["mcp_schema_tokens"] = count_tokens(prompt)

            response = await self._llm.generate_async(
                messages=[{"role": "user", "content": prompt}],
                tracer=tracer,
                callbacks=callbacks
            )
            try:
                response = self._strip_code_fences(response)

                # Count tool call output tokens
                local_token_counts["tool_call_output_tokens"] += count_tokens(response)

                # Parse response using tool_call_format strictly. A format
                # mismatch is a real failure the paper should report — not a
                # silent JSON fallback.
                tc_fmt_for_parse = fc._shared_tc_fmt()
                try:
                    parsed_response = shared_format.deserialize_strict(response, tc_fmt_for_parse)
                except shared_format.FormatViolation:
                    format_violations += 1
                    raise ValueError("Format violation: response is not valid in the configured tool_call_format")
                # TRON-specific: emitting plain JSON for 2+ same-shape objects skips
                # TRON's compression feature. Count as format violation so exp2 numbers
                # reflect "model actually used TRON" rather than "model emitted JSON
                # that happens to parse as TRON".
                if tc_fmt_for_parse == shared_format.ToolFormat.TRON and \
                        not shared_format.tron_uses_class_when_possible(response, parsed_response):
                    format_violations += 1
                # Normalize top-level keys to lowercase. Gemma-3 (and some others) drift
                # to capitalized "Action:" / "Thought:" / "Answer:" mid-trajectory; the
                # ReAct contract uses lowercase. Accept either casing rather than
                # counting every step as a violation.
                if isinstance(parsed_response, dict):
                    parsed_response = {
                        (k.lower() if isinstance(k, str) and k.lower() in ("thought", "action", "answer") else k): v
                        for k, v in parsed_response.items()
                    }
                if not isinstance(parsed_response, dict) or "thought" not in parsed_response:
                    format_violations += 1
                    raise ValueError("Invalid response format")
                self._add_history(
                    history_type=f"Step {iter_num + 1}",
                    message="",
                )
                if "answer" in parsed_response:
                    self._add_history(
                        history_type="answer",
                        message=parsed_response["answer"]
                    )
                    await self._send_callback_message(
                        callbacks=callbacks,
                        iter_num=iter_num,
                        thought=parsed_response["thought"],
                        answer=parsed_response["answer"]
                    )
                    # Record local token counts and format in trace
                    with tracer.sprout() as t:
                        t.add({
                            "type": "agent_format_metrics",
                            "tool_format": self._config.tool_format,
                            "tool_call_format": self._config.tool_call_format or self._config.tool_format,
                            "local_token_counts": local_token_counts,
                            "format_violations": format_violations,
                        })
                    return AgentResponse(
                        name=self._name,
                        class_name=self.__class__.__name__,
                        response=parsed_response["answer"],
                        trace_id=tracer.trace_id
                    )
                if "action" in parsed_response:
                    self._add_history(
                        history_type="thought",
                        message=parsed_response["thought"]
                    )
                    action = parsed_response["action"]
                    # TOON gotcha: model often emits `arguments: {}` (a JSON-style empty literal),
                    # which TOON's parser reads as the string '{}'. Coerce empty inline literals
                    # back to a real empty dict before tool dispatch so a single empty-args quirk
                    # doesn't poison the run.
                    if isinstance(action, dict) and "arguments" in action:
                        action["arguments"] = shared_format.coerce_empty_inline_literal(action["arguments"])
                        if isinstance(action["arguments"], str):
                            # Still a string after coercion: real shape mismatch, count it.
                            format_violations += 1
                    if not isinstance(action, dict) or "server" not in action or "tool" not in action:
                        self._add_history(history_type="action", message=str(action))
                        self._add_history(history_type="result", message="Invalid action")
                        await self._send_callback_message(
                            callbacks=callbacks,
                            iter_num=iter_num,
                            thought=parsed_response["thought"],
                            action=parsed_response["action"],
                            result="Invalid action"
                        )
                    else:
                        self._add_history(
                            history_type="action",
                            message=f"Using tool `{action['tool']}` in server `{action['server']}`"
                        )
                        self._add_history(
                            history_type="action input",
                            message=str(action.get("arguments", "none"))
                        )
                        try:
                            tool_result = await self.call_tool(action, tracer=tracer, callbacks=callbacks)
                            tool_content = tool_result.content[0]
                            tool_summary = None
                            if not isinstance(tool_content, TextContent):
                                raise ValueError("Tool output is not a text")
                            if self._config.summarize_tool_response:
                                context = json.dumps(action, indent=2)
                                tool_summary = await self.summarize_tool_response(
                                    tool_content.text,
                                    context=context,
                                    tracer=tracer
                                )
                                result_text = tool_summary
                            else:
                                result_text = tool_content.text

                            # Serialize tool result in target format for history
                            if fc.format != ToolFormat.JSON:
                                serialized_result = fc.serialize({"tool_result": result_text})
                            else:
                                serialized_result = result_text
                            self._add_history(history_type="result", message=serialized_result)

                            # Count tool result tokens
                            local_token_counts["tool_result_tokens"] += count_tokens(serialized_result)

                            await self._send_callback_message(
                                callbacks=callbacks,
                                iter_num=iter_num,
                                thought=parsed_response["thought"],
                                action=parsed_response['action'],
                                result=result_text
                            )
                        except Exception as e:
                            self._add_history(history_type="result", message=str(e)[:300])
                            await self._send_callback_message(
                                callbacks=callbacks,
                                iter_num=iter_num,
                                thought=parsed_response["thought"],
                                action=parsed_response['action'],
                                result=str(e)
                            )

                elif "result" in parsed_response:
                    self._add_history(
                        history_type="thought",
                        message=parsed_response["thought"]
                    )
                    self._add_history(
                        history_type="result",
                        message=parsed_response["result"]
                    )
                    await self._send_callback_message(
                        callbacks=callbacks,
                        iter_num=iter_num,
                        thought=parsed_response["thought"],
                        result=parsed_response["result"]
                    )
                else:
                    raise ValueError("Invalid response format")

            except (json.JSONDecodeError, ValueError) as e:
                self._logger.error("Failed to parse response: %s", str(e))
                self._add_history(
                    history_type="error",
                    message="I encountered an error in parsing LLM response. Let me try again."
                )
                send_message(callbacks, message=CallbackMessage(
                    source=__file__,
                    type=MessageType.LOG,
                    data={
                        "step": iter_num + 1,
                        "error": f"Failed to parse response: {str(e)}"
                    }
                ))
            except Exception as e:
                self._logger.error("Failed to process response: %s", str(e))
                self._add_history(
                    history_type="error",
                    message="I encountered an unexpected error. Let me try a different approach."
                )
                send_message(callbacks, message=CallbackMessage(
                    source=__file__,
                    type=MessageType.LOG,
                    data={
                        "step": iter_num + 1,
                        "error": f"Failed to process response: {str(e)}"
                    }
                ))

        # Record local token counts even on max-iteration exit
        with tracer.sprout() as t:
            t.add({
                "type": "agent_format_metrics",
                "tool_format": self._config.tool_format,
                "tool_call_format": self._config.tool_call_format or self._config.tool_format,
                "local_token_counts": local_token_counts,
                "format_violations": format_violations,
            })

        return AgentResponse(
            name=self._name,
            class_name=self.__class__.__name__,
            response="I'm sorry, but I couldn't find a satisfactory answer within the allowed number of iterations.",
            trace_id=tracer.trace_id
        )

    def get_history(self) -> str:
        """
        Retrieve the agent's conversation history.

        Returns:
            str: A string representation of the agent's conversation history.
        """
        return "\n".join(self._history)

    def clear_history(self):
        """
        Clear the agent's conversation history.
        """
        self._history = []

    def reset(self):
        """Reset the agent."""
        self.clear_history()

    @staticmethod
    async def _send_callback_message(
            callbacks,
            iter_num: int,
            thought: str = "",
            action: str = "",
            result: str = "",
            answer: str = ""
    ):
        """Send log messages."""
        logs = []
        if thought:
            logs.append(("thought", thought))
        if action:
            logs.append(("action", action))
        if result:
            logs.append(("result", result))
        if answer:
            logs.append(("answer", answer))

        data = OrderedDict({"Iteration": iter_num + 1})
        for tag, value in logs:
            data[tag] = value
        send_message(callbacks, message=CallbackMessage(
            source=__file__,
            type=MessageType.LOG,
            data=data
        ))
        data = [
            f"{'=' * 66}\n",
            f"Iteration: {iter_num + 1}\n",
            f"{'-' * 66}\n",
        ]
        for tag, value in logs:
            data.append(f"\033[32m{tag.capitalize()}: {value}\n\n\033[0m")
        await send_message_async(
            callbacks,
            message=CallbackMessage(
                source=__file__,
                type=MessageType.LOG,
                metadata={
                    "event": "plain_text",
                    "data": "".join(data)
                }
            )
        )
