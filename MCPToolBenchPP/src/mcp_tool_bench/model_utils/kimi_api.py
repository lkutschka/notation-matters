# #!/usr/bin/python
# # -*- coding: UTF-8 -*-
import json
import logging
import requests
from typing import List, Dict, Any, Optional
import os
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, '../../..')))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, '../..')))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, '../')))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, './')))

from src.mcp_tool_bench.model_utils.base_api import *
from src.mcp_tool_bench.global_variables import settings


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

class KimiModelAPIProvider(BaseModelAPIProvider):
    """
        https://platform.moonshot.ai/docs/api/chat#public-service-address
    """
    def api_chat(self, messages: List, **kwargs) -> Dict[str, Any]:
        """
            Kimi model: "K2"
        """
        try:
            model = self.model_name
            if model == "" or model is None:
                model = "kimi-k2-0711-preview"
            response = call_kimi_k2_chat(messages, model)
            tools, completion, reasoningContent = post_process_kimi_response(response)
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
        """
        try:
            model = self.model_name
            if model == "" or model is None:
                model = "kimi-k2-0711-preview"
            response = call_kimi_k2_tools(messages, tools, model)
            tool_result = post_process_function_call_kimi(response)
            tool_call_mapped, completion, reasoningContent = function_call_result_common_mapper(tool_result)

            result = {
                KEY_FUNCTION_CALL: tool_call_mapped,
                KEY_COMPLETION: "", 
                KEY_REASON_CONTENT: ""
            }
            # print (f"KimiModelAPIProvider debug api_function_call result return {result}")
            return result

        except Exception as e:
            logging.error(e)
            return {}
        
def call_kimi_k2_chat(messages, model_name):
    from openai import OpenAI

    client = OpenAI(
        api_key = settings.KIMI_API_KEY,
        base_url = "https://api.moonshot.ai/v1",
    )
    
    completion = client.chat.completions.create(
        model = model_name,
        messages = messages,
        temperature = 0.3,
    )
    return completion

def call_kimi_k2_tools(messages, tools, model_name):
    import logging
    import urllib3
    from openai import OpenAI
    
    # Completely disable all logging
    logging.disable(logging.CRITICAL)
    urllib3.disable_warnings()
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)
    logging.getLogger("openai").setLevel(logging.CRITICAL)

    client = OpenAI(
        api_key = settings.KIMI_API_KEY,
        base_url = "https://api.moonshot.ai/v1",
    )
    
    return client.chat.completions.create(
        model = model_name,
        messages = messages,
        tools = tools,
        temperature = 0.3,
    )
    return completion

def post_process_kimi_response(response):
    if response is None:
        return {}
    tools = {}
    completion = ""
    reasoningContent = ""  
    try:
        completion = response.choices[0].message.content
    except Exception as e:
        logging.error(e)
    return tools, completion, reasoningContent

def post_process_function_call_kimi(response):
    if response is None:
        return {}
    try:
        if "error" in response:
            logging.error(f"post_process_function_call_kimi error {response}")
            return {}
        first_tool_call = response.choices[0].message.tool_calls[0]
        tool_call = {
            "id": first_tool_call.id,
            "function": {
                "name": first_tool_call.function.name,
                "arguments": first_tool_call.function.arguments
            }
        }
        return tool_call
    except Exception as e:
        logging.error(f"post_process_function_call_kimi {e}")
        return {}

if __name__ == '__main__':
    gpt_api_provider = KimiModelAPIProvider(MODEL_SELECTION_KIMI_K2)
    
    # Test normal conversation
    # chat
    user_prompt = "Hello, how are you?"
    system_prompt = "You are a helpful assistant."
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    result = gpt_api_provider.api_chat(messages)
    print("KIMI API Chat Response:", result)
    
    # Test function calling
    user_prompt = "Weather query template"
    system_prompt = ""
    try:
        messages = [{"role": "user", "content": user_prompt}]
        current_dir = os.path.dirname(os.path.abspath(__file__))
        package_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        input_file = os.path.join(package_dir, "mcp/tools/demo/demo_tools.json")
        tools = json.load(open(input_file, "r", encoding="utf-8"))
        wrappered_tools = tools_openai_wrapper(tools)
        result = gpt_api_provider.api_function_call(messages, wrappered_tools)
        print("KIMI Function Call Response:", result)
    except FileNotFoundError:
        print("Demo tools file not found, skipping function call test")
