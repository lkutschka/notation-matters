from typing import List, Dict, Any
from utils.prompt import user_prompt_template_generate_query, system_prompt_template_generate_query, system_prompt_template_generate_query_for_single_tool, system_prompt_template_generate_query_for_filesystem
from utils.prompt_reference import candidate_reference_list, special_needs_description_list
import json
from src.mcp_tool_bench.model_utils.model_provider import _global_model_provider
from src.mcp_tool_bench.global_variables import *
import html
import re
from bs4 import BeautifulSoup
from tqdm import tqdm

def decode_html_entities(s):
    """Decode HTML entities"""
    # Try using html.unescape
    first_decode = html.unescape(s)
    # Check if still contains undecoded entities
    if "&" in first_decode and ";" in first_decode:
        # Use BeautifulSoup for further decoding
        soup = BeautifulSoup(first_decode, "html.parser")
        second_decode = soup.get_text()
        return second_decode
    return first_decode

def auto_fix_unclosed_quotes(data):
    """
    Automatically detect and fix unclosed quotes in strings.
    """
    if isinstance(data, list):
        return data

    """
    Automatically add space after colon in key-value pairs, e.g., convert 'key:value' to 'key: value'
    """
    # Use regex to match cases where colon is not followed by space, and add space
    data = re.sub(r'(?m)^(\s*[^#\s][^:]*):([^\s])', r'\1: \2', data)
    
    lines = data.split("\n")
    fixed_lines = []
    for line in lines:
        # Detect and fix unclosed quotes
        if line.count('"') % 2 != 0:
            line = line + '"'  # Append a quote to close
        fixed_lines.append(line)
    return "\n".join(fixed_lines)

def process_response(response_text):
    """Process GPT response text"""
    if not response_text:
        return ""
    
    raw_val = decode_html_entities(response_text)
    raw_val = auto_fix_unclosed_quotes(raw_val)
    decoded_json_str = html.unescape(raw_val)
    decoded_json_str = decoded_json_str.replace("```json\n", "").replace("```", "").replace("\n", "")
    return decoded_json_str

def generate_query_and_function_calls(extraction_results: List[List[Dict]], category: str) -> List[Dict]:
    """
    Generate user questions and tool call examples based on extracted tools list
    
    Args:
        extraction_results: Tools extraction result list
        category: Data category
        
    Returns:
        List[Dict]: Generated data list
    """
    # gpt_api = GPTAPI()
    generated_data = []
    lang = "English"
    # Add progress bar for processing extraction results
    for tools_list in tqdm(extraction_results, desc="Generating queries and function calls", unit="tool_list"):
        # Here should call GPT API to generate query and function_call_label

        user_prompt = user_prompt_template_generate_query.format(tools=tools_list)
        # system_prompt = system_prompt_template_generate_query_for_filesystem.format(candidate_count=5, language=lang)
        candidate_reference = candidate_reference_list.get(category, {})
        special_needs_description = special_needs_description_list.get(category, "")
        system_prompt = system_prompt_template_generate_query.format(candidate_count=10, language=lang, candidate_reference=candidate_reference, special_needs_description=special_needs_description)

        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
        # print("messages: ", messages)
        model_provider = _global_model_provider[MODEL_SELECTION_GPT4O_ANT] if MODEL_SELECTION_GPT4O_ANT in _global_model_provider else None
        output = model_provider.api_chat(messages, wait_time=5) if model_provider is not None else {}
        print("output: ", output)
        raw_response = output[KEY_COMPLETION] if KEY_COMPLETION in output else ""
        
        # Normal chat: process string
        if isinstance(raw_response, str):
            result =  process_response(raw_response)
        # result = gpt_api.call(user_prompt, system_prompt, wait_time=10)
        
        print("result: ", result)
        print("type(result): ", type(result))

        try:
            result = json.loads(result)
            generated_data.append(result)
        except Exception as e:
            # logging.error(f"Error processing response: {e}")
            continue
    
    return generated_data
