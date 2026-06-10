import json
from typing import List, Dict, Any, Optional
from ..global_variables import *

class BaseModelAPIProvider:
    """

        Usage:
            model_provider = _global_model_provider[MODEL_SELECTION_GPT4O] if MODEL_SELECTION_GPT4O in _global_model_provider else None
            result = model_provider.api_chat(messages) if model_provider is not None else {}
            completion = result[KEY_COMPLETION]

    """

    def __init__(self, model_name: str):
        """
        Args:
            model_name: e.g. claude-3.7
        """
        self.model_name = model_name

    def api_chat(self, messages: List[Any], **kwargs) -> Dict[str, Any]:
        """        
        Args:
            messages: List[Any]
            **kwargs: other parameters
        
        Returns:
            str: response
        """
        result = {
            KEY_FUNCTION_CALL: {},
            KEY_COMPLETION: "", 
            KEY_REASON_CONTENT: ""
        }
        return result
    
    def api_function_call(self, messages: List[Any], tools: list, **kwargs) -> Dict[str, Any]:
        """
        
        Args:
            messages: list of json message
            tools: available tool json
            **kwargs: other parameters
        
        Returns:
            Dict: result
        """
        result = {
            KEY_FUNCTION_CALL: {},
            KEY_COMPLETION: "", 
            KEY_REASON_CONTENT: ""
        }
        return result

def function_call_result_common_mapper(tool_call):
    """
        This wrapper is a common mapper to wrap the result of OpenAI/Claude Stype function call results, thinking/no thinking models
        Args:
            tool_call: 
                {
                    "id": "call_d6f4ed29ce614390b99a05",
                    "function": {
                        "arguments": "{\"url\": \"https://www.stackoverflow.com\", \"browserType\": \"chromium\"}",
                        "name": "playwright_navigate"
                    },
                    "type": "function",
                    "index": 0
                }

        Return:
            tools_choice_response 

                {
                    "function_name": "playwright_navigate",
                    "function_arguments": "{\"url\": \"https://www.stackoverflow.com\", \"browserType\": \"chromium\"}",
                    "is_function_call": true,
                    "id": "call_d6f4ed29ce614390b99a05"
                } 
            completion: str
            reasoningContent: str
    """
    if tool_call is None or len(tool_call) == 0:
        return {}, "", ""

    tools_choice_response = {
        'function_name': '',
        'function_arguments': '',
        'is_function_call': False, 
        'id': ''
    }
    completion = ""
    reasoningContent = ""
    try:
        tool_id = tool_call["id"] if "id" in tool_call else ""
        function = tool_call["function"] if "function" in tool_call else {}
        function_arguments = function["arguments"] if "arguments" in function else {}
        function_name = function["name"] if "name" in function else ""

        tools_choice_response["is_function_call"] = True 
        tools_choice_response["function_name"] = function_name
        tools_choice_response["function_arguments"] = function_arguments
        tools_choice_response["id"] = tool_id
    except Exception as e:
        logging.error(f"Failed to run tool_result_to_claude_mapper {e}")
    return tools_choice_response, completion, reasoningContent

def tool_call_parameter_wrapper(model: str, tool_id: str, tool_name: str, tool_arguments: dict):
    
    message_tool_parameter = {}
    if "gpt" in model:
        # OpenAI Claude Format
        message_tool_parameter = tool_call_param_openai_wrapper(tool_id, tool_name, tool_arguments)
    elif "claude" in model:
        # Claude Format
        message_tool_parameter = tool_call_param_claude_wrapper(tool_id, tool_name, tool_arguments)
    elif "qwen" in model:
        # Qwen Wrapper
        message_tool_parameter = tool_call_param_qwen_wrapper(tool_id, tool_name, tool_arguments)
    else:
        message_tool_parameter = tool_call_param_openai_wrapper(tool_id, tool_name, tool_arguments)
    return message_tool_parameter

def tool_call_result_wrapper(model: str, tool_id: str, tool_name: str, tool_result: dict):
    
    message_tool_result = {}
    if "gpt" in model:
        # OpenAI Claude Format
        message_tool_result = tool_call_result_openai_wrapper(tool_id, tool_name, tool_result)
    elif "claude" in model:
        # Claude Format
        message_tool_result = tool_call_result_claude_wrapper(tool_id, tool_result)
    elif "qwen" in model:
        # Qwen Wrapper
        message_tool_result = tool_call_result_qwen_wrapper(tool_id, tool_result)
    else:
        message_tool_result = tool_call_result_openai_wrapper(tool_id, tool_name, tool_result)
    return message_tool_result

def tools_openai_wrapper(tools):
    tools_wrapped = [{
        "type": "function",
        "function":{
            "name": tool["name"] if "name" in tool else "", 
            "description": tool["description"] if "description" in tool else "",
            "parameters": tool["input_schema"] if "input_schema" in tool else {}
        }
    } for tool in tools]
    return tools_wrapped

def tool_call_param_openai_wrapper(tool_id: str, tool_name: str, arguments: Dict, **kwargs):
    
    context_id = kwargs["context_id"] if "context_id" in kwargs else ""
    session_id = kwargs["session_id"] if "session_id" in kwargs else ""
    
    oai_tool_call = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                        "id": tool_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(arguments),
                        },
            }
        ],
    }
    if context_id != "":
        oai_tool_call["contextId"] = context_id
    if session_id != "":
        oai_tool_call["sessionId"] = session_id
    return oai_tool_call

def tool_call_param_claude_wrapper(tool_id: str, tool_name: str, arguments: Dict):
    claude_tool_assistant = {
        "role": "assistant",
        "content": [
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": tool_name,
                            "input": arguments
                        }
        ]
    }
    return claude_tool_assistant

def tool_call_param_claude_bedrock_wrapper(tool_id: str, tool_name: str, arguments: Dict):
    claude_tool_assistant = {
        "role": "assistant",
        "content": [
            {
                "toolUse": { 
                    "id": tool_id,
                    "name": tool_name,
                    "input": arguments
                }
            }
        ]
    }
    return claude_tool_assistant

def tool_call_param_qwen_wrapper(tool_id: str, tool_name: str, arguments: Dict):
    qwen_tool_assistant = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tool_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(arguments)
                }
            }
        ]
    }
    return qwen_tool_assistant

def tool_call_result_openai_wrapper(tool_id: str, tool_name: str, result: Any):
    """
    """
    oai_tool_result_msg = {
        "tool_call_id": tool_id,
        "role": "tool",
        "name": tool_name,
        "content": json.dumps(result), # Must be a string
    }
    return oai_tool_result_msg

def tool_call_result_claude_wrapper(tool_id: str, result: Any):
    """
    """
    claude_tool_result_msg = {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_id, # from the API response
                "content": json.dumps(result) # from running your tool
            }
        ]
    }
    return claude_tool_result_msg

def tool_call_result_claude_bedrock_wrapper(tool_id: str, result: Any):
    """
    """
    tool_result_msg = {
        "role": "user",
        "content": [
            {
                "toolResult": {
                    "toolUseId": tool_id,
                    "content": [
                        {"text": json.dumps(result)}
                    ],
                }
            }
        ]
    }
    return tool_result_msg
def tool_call_result_qwen_wrapper(tool_id: str, result: Any):
    """
    """
    qwen_tool_result_msg = {
        "role": "tool",
        "content": [{"type": "text", "text": json.dumps(result)}],
        "tool_call_id": tool_id
    }
    return qwen_tool_result_msg
