# #!/usr/bin/python
# # -*- coding: UTF-8 -*-
import logging
from typing import List, Dict, Any
import os
import sys
from openai import OpenAI

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, '../../..')))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, '../..')))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, '../')))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, './')))

from src.mcp_tool_bench.model_utils.base_api import BaseModelAPIProvider, function_call_result_common_mapper, KEY_FUNCTION_CALL, KEY_COMPLETION, KEY_REASON_CONTENT

class CustomOpenAIAPIProvider(BaseModelAPIProvider):
    """
    Custom OpenAI-compatible API provider that allows setting custom model name, base URL, and API key.
    This can be used with various OpenAI-compatible services like Ollama, LocalAI, vLLM, etc.
    """
    def __init__(self, model_name: str, base_url: str, api_key: str = "not-needed"):
        """
        Initialize the custom OpenAI-compatible API provider.

        Args:
            model_name: The name of the model to use
            base_url: The base URL of the OpenAI-compatible API (e.g., "http://localhost:11434/v1")
            api_key: The API key (some local services don't require a real key)
        """
        super().__init__(model_name)
        self.base_url = base_url
        self.api_key = api_key
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def api_chat(self, messages: List, **kwargs) -> Dict[str, Any]:
        """
        Custom OpenAI-compatible chat completion.
        """
        try:
            model = self.model_name
            if not model:
                raise ValueError("Model name is required for custom API provider")

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.3),
                **{k: v for k, v in kwargs.items() if k not in ['temperature', 'wait_time']}
            )
            completion, reasoning_content = self._post_process_chat_response(response)
            result = {
                KEY_FUNCTION_CALL: {},
                KEY_COMPLETION: completion,
                KEY_REASON_CONTENT: reasoning_content
            }
            return result

        except Exception as e:
            logging.error(f"Failed to process Custom OpenAI API api_chat: {e}")
            return {}

    def api_function_call(self, messages: List, tools: List, **kwargs) -> Dict[str, Any]:
        """
        Custom OpenAI-compatible function calling (tool calling).
        Args:
            messages: List of message [{}, {}]
            tools: List of tool definitions [{type: "function", function: {name: "", description: "", parameters: {}}}]
        """
        try:
            model = self.model_name
            if not model:
                raise ValueError("Model name is required for custom API provider")

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=kwargs.get("temperature", 0.3),
                **{k: v for k, v in kwargs.items() if k not in ['temperature', 'wait_time']}
            )
            tool_call = self._post_process_function_call_response(response)
            tool_call_mapped, completion, reasoning_content = function_call_result_common_mapper(tool_call)

            result = {
                KEY_FUNCTION_CALL: tool_call_mapped,
                KEY_COMPLETION: completion,
                KEY_REASON_CONTENT: reasoning_content
            }
            return result

        except Exception as e:
            logging.error(f"Failed to process Custom OpenAI API api_function_call: {e}")
            return {}

    def _post_process_chat_response(self, response):
        """
        Processes the response from custom OpenAI-compatible chat completion.
        """
        if response is None or not response.choices:
            return "", ""
        completion_content = ""
        if response.choices[0].message.content:
            completion_content = response.choices[0].message.content
        return completion_content, ""

    def _post_process_function_call_response(self, response):
        """
        Processes the response from custom OpenAI-compatible API for function calls.
        Extracts the tool call details.
        """
        if response is None or not response.choices or not response.choices[0].message:
            return {}

        try:
            message = response.choices[0].message
            if message.tool_calls:
                first_tool_call = message.tool_calls[0]
                if first_tool_call.type == "function" and first_tool_call.function:
                    tool_call = {
                        "id": first_tool_call.id,
                        "function": {
                            "name": first_tool_call.function.name,
                            "arguments": first_tool_call.function.arguments
                        }
                    }
                    return tool_call
            return {}
        except Exception as e:
            logging.error(f"Failed to _post_process_function_call_response error {e}")
            return {}

    def get_model_info(self):
        """
        Returns information about the custom API provider configuration.
        """
        return {
            "model_name": self.model_name,
            "base_url": self.base_url,
            "api_key": "***" if self.api_key else None
        }

if __name__ == '__main__':
    # Example usage
    try:
        # Example with Ollama (local deployment)
        custom_provider = CustomOpenAIAPIProvider(
            model_name="llama3.2",
            base_url="http://localhost:11434/v1",
            api_key="not-needed"
        )

        messages = [{"role": "user", "content": "Hello, how are you?"}]
        result = custom_provider.api_chat(messages)
        print("Custom API Chat Response:", result)
        print("Provider Info:", custom_provider.get_model_info())

    except Exception as e:
        print(f"Example failed (this is expected if no local service is running): {e}")
