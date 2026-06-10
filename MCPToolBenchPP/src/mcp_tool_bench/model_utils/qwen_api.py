import json
import logging
from typing import List, Dict, Any, Optional
from .base_api import *
from ..global_variables import settings
import requests

class QwenModelAPIProvider(BaseModelAPIProvider):

    def api_chat(self, messages: List, **kwargs) -> Dict[str, Any]:
        """
            Qwen model: "qwen-max", "qwen-plus"
        """
        try:
            model = self.model_name
            if model == "" or model is None:
                model = "qwen-plus"

            response = call_qwen_messages_model_selection(messages, self.model_name)
            tools, completion, reasoningContent = post_process_qwen_response(response)
            result = {
                KEY_FUNCTION_CALL: tools,
                KEY_COMPLETION: completion, 
                KEY_REASON_CONTENT: reasoningContent
            }
            return result

        except Exception as e:
            logging.error(f"Failed to process api_chat")
            return {}
    
    def api_function_call(self, messages: List, tools: List, **kwargs) -> Dict[str, Any]:
        """
        Args:
            messages: List of message [{}, {}]
            tools: List
        Returns:
            result: Dict: ,
            {
                'tools': 
                    {
                        'function_name': 'playwright_navigate', 'function_arguments': '{"url": "https://www.stackoverflow.com", "browserType": "chromium"}', 
                        'is_function_call': True, 
                        'id': 'call_6cb5d88bb3cf4884aadc03'
                    }, 
                'completion': '', 
                'reason': ''
            }
        """
        try:
            model = self.model_name
            if model == "" or model is None:
                model = "qwen-plus"
            messages, tools, model
            response = call_qwen_tool_calls_model_selection(messages, tools, model)
            tool_call = post_process_function_call_qwen_common(response)
            tool_call_mapped, completion, reasoningContent = function_call_result_common_mapper(tool_call)

            result = {
                KEY_FUNCTION_CALL: tool_call_mapped,
                KEY_COMPLETION: "", 
                KEY_REASON_CONTENT: ""
            }
            print (f"AntQwenModelAPIProvider debug api_function_call result return {result}")

            return result

        except Exception as e:
            logging.error(f"QwenModelAPIProvider {e}")
            return {}

def call_qwen_messages_model_selection(messages: List, model: str):
    """
        Reference doc: https://help.aliyun.com/zh/model-studio/use-qwen-by-calling-api#b30677f6e9437
        Input: 
            messages: List[Dict]
    """
    try:
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        api_key = settings.QWEN_API_KEY
        if api_key is None:
            raise ValueError("qwen_general_api.py call_qwen_max_user_prompt api_key not found, please check .env file key QWEN_API_KEY")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": messages,
        }
        data = json.dumps(data).encode("utf-8")
        response = requests.post(url, headers=headers, data=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print("Qwen Response:", result["choices"][0]["message"]["content"])
        else:
            print(f"API Return Failed with Status (Status Code: {response.status_code}): {response.text}")
        return response
    except Exception as e:
        logging.error(e)
        return None


def call_qwen_user_prompt_model_selection(user_prompt: str, model: str):
    """
        Reference doc: https://help.aliyun.com/zh/model-studio/use-qwen-by-calling-api#b30677f6e9437
    """
    try:
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        api_key = settings.QWEN_API_KEY
        if api_key is None:
            raise ValueError("qwen_general_api.py call_qwen_max_user_prompt api_key not found, please check .env file key QWEN_API_KEY")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        data = json.dumps(data).encode("utf-8")
        response = requests.post(url, headers=headers, data=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            print("Qwen Response:", result["choices"][0]["message"]["content"])
        else:
            print(f"API Return Failed with Status (Status Code: {response.status_code}): {response.text}")
        return response
    except Exception as e:
        logging.error(e)
        return None


def post_process_qwen_response(response):
    if response is None:
        return {}
    tools, completion,reasoningContent  = {}, "", ""

    res_json = {}      
    try:
        print (f"post_process_function_call_qwen_base input response {response} and type {type(response)}")
        res_json = json.loads(response.content)
    except json.decoder.JSONDecodeError:
        print("Not Valid Json Format")
        return ''
    try:
        # x = res_json["data"]["values"]["data"]
        completion = res_json["choices"][0]["message"]["content"]
        usage = res_json["usage"] if "usage" in res_json else {}
    except Exception as e:
        logging.error(e)
    return tools, completion, reasoningContent



def call_qwen_tool_calls_model_selection(messages, tools, model):
    """
        Args:
            messages: list of dict 
            tools: list of dict
        return:
            {"choices":[{"message":{"content":"","role":"assistant","tool_calls":[{"index":0,"id":"call_f8d9f219ee034156985f6a","type":"function","function":{"name":"get_current_weather","arguments":"{\"location\": \"上海\"}"}}]},"finish_reason":"tool_calls","index":0,"logprobs":null}],"object":"chat.completion","usage":{"prompt_tokens":266,"completion_tokens":20,"total_tokens":286,"prompt_tokens_details":{"cached_tokens":0}},"created":1750987730,"system_fingerprint":null,"model":"qwen-plus","id":"chatcmpl-3bd1954c-8594-98e1-957b-9fda39ac73fc"}
        doc: https://help.aliyun.com/zh/model-studio/qwen-function-calling
    """
    try:
        api_key = settings.QWEN_API_KEY
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {api_key}",
        }
        data = {
                "stream": False,
                "model": model,
                "messages": messages,
                "tools": tools
        }
        data = json.dumps(data).encode("utf-8")
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            result = response.json()
            print("Qwen Response:", result["choices"][0]["message"]["content"])
        else:
            print(f"API Return Failed with Status (Status Code: {response.status_code}): {response.text}")
        return response
    except Exception as e:
        print (e)
        return None

def post_process_function_call_qwen_common(response):
    """
        tool_call:
            {
                "id": "call_6fcd208b442c4c12b1b419",
                "function": {
                  "arguments": "{\"location\": \"\u4e0a\u6d77\u5e02\"}",
                  "name": "get_current_weather"
                },
                "type": "function",
                "index": 0
            }
    """
    if response is None:
        return {}

    tools = {}
    completion = ""
    reasoningContent = ""  

    res_json = {}      
    try:
        content = response.content
        logging.info(f"post_process_function_call_qwen_base content {content}")
        res_json = json.loads(content)

    except json.decoder.JSONDecodeError:
        print("Not Valid Json Format" + content)
        return {}
    try:
        choice = res_json["choices"][0] if len(res_json["choices"]) > 0 else {}
        finish_reason = choice["finish_reason"] if "finish_reason" in choice else "" # tool_calls
        message = choice["message"] if "message" in choice else {}
        tool_calls = message["tool_calls"] if "tool_calls" in message else []
        tool_call = tool_calls[0] if len(tool_calls) > 0 else {}
        return tool_call
    except Exception as e:
        logging.error(e)
        return {}
