import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, '../../..')))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, '../..')))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, '../')))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, './')))

from src.mcp_tool_bench.agents.base_tool_call_agent.prompt import *
from src.mcp_tool_bench.evaluation.evaluation_utils import estimate_pass_at_k, base_error_analysis
import html
import re
from bs4 import BeautifulSoup
from src.mcp_tool_bench.global_variables import *
from src.mcp_tool_bench.model_utils.model_provider import get_model_provider
from src.mcp_tool_bench.model_utils.base_api import *
import json
import logging
from typing import List, Dict, Tuple
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
    Automatically add space after colon in key-value pairs, e.g., convert 'key:value' to 'key: value'
    """
    if isinstance(data, list):
        return data
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

_THINK_TAG_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)
_FIRST_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def process_response(response_text):
    """Process LLM judge response text.

    Reasoning models (Qwen3, DeepSeek-R1, etc.) emit <think>...</think> blocks
    before the actual JSON. Older code only stripped ```json``` fences and
    newlines, so json.loads silently failed on every judge call when the
    cluster judge is a thinking model — which made every param_pass score 0
    across all benchpp runs.
    """
    if not response_text:
        return ""

    raw_val = decode_html_entities(response_text)
    raw_val = auto_fix_unclosed_quotes(raw_val)
    decoded_json_str = html.unescape(raw_val)
    # Strip <think>...</think> blocks (Qwen3 / DeepSeek-R1 reasoning preamble)
    decoded_json_str = _THINK_TAG_RE.sub("", decoded_json_str)
    decoded_json_str = decoded_json_str.replace("```json\n", "").replace("```", "")
    # If there's leading explanatory text before the JSON, extract first {...}
    if not decoded_json_str.lstrip().startswith("{"):
        m = _FIRST_JSON_OBJECT_RE.search(decoded_json_str)
        if m:
            decoded_json_str = m.group(0)
    decoded_json_str = decoded_json_str.replace("\n", "")
    return decoded_json_str

def check_ast(pred_tool_result_list: List[Dict], label_result_list: List[Dict], query: str, model_name: str = MODEL_SELECTION_GPT4O) -> Tuple:
    """
        Check the AST of tool calls
        model_name: required, the LLM as a judge can verify the parameters are aligned. For example, the "query" used in search tools may be
        rewrited by Function Call models. And LLM as a judge need to determine if the query is correctedly rewritten that match the original query.
        Default: Using GPT4o

        Returns:
            Tuple of (tool_correctness, parameter_correctness, judge_usage)
            judge_usage is a dict with prompt_tokens, completion_tokens, total_tokens, cost_usd
    """
    # BENCHPP_SKIP_JUDGE=1: defer the LLM judge step. Used when the model under
    # test consumes all GPUs on the node (e.g. Llama-4-Scout at TP=2 on a 2-GPU
    # node) and the judge has nowhere to run co-resident. Generate phase stores
    # function_call_result; rerun_benchpp_judge.slurm replays the judge offline.
    if os.environ.get("BENCHPP_SKIP_JUDGE") == "1":
        return 0, 0, {}
    try:
        if pred_tool_result_list == label_result_list:
            return True, True, {}
        label_step = 1
        predict_step = 1
        if (label_step == 1 and predict_step == 1):
            user_prompt = user_prompt_template_ast.format(pred_tool_result_list=pred_tool_result_list, label_result_list=label_result_list, query=query)
            system_prompt = system_prompt_template_ast_single.format()
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
            model_provider = get_model_provider(model_name)
            output = model_provider.api_chat(messages, wait_time=5) if model_provider is not None else {}
            judge_usage = output.get(KEY_USAGE, {}) if isinstance(output, dict) else {}
            raw_response = output[KEY_COMPLETION] if KEY_COMPLETION in output else ""
            # Normal chat: process string
            if isinstance(raw_response, str):
                result =  process_response(raw_response)
            try:
                result = json.loads(result)
            except Exception as e:
                logging.error(f" Failed to parse json {e}")
                return False, False, judge_usage
            # print("[debug]  check_ast result: ", result)
            tool_correctness = result["tool_correctness"] if "tool_correctness" in result else 0
            parameter_correctness = result["parameter_correctness"] if "parameter_correctness" in result else 0

        else:
            ## multiple
            return False, False, {}
        return tool_correctness, parameter_correctness, judge_usage

    except Exception as e:
        print (f"check_ast failed with error {e}")
        return 0, 0, {}

def check_single_tool_call_dag(pred_tool_result: Dict, label_result: Dict) -> Tuple[bool, bool]:
    # implementation
    # print("[debug] pred_tool_result:", pred_tool_result)
    # print("[debug] label_result:", label_result)
    label_tool_name = label_result["name"] if "name" in label_result else ""
    similar_tools = label_result.get("similar_tools", [])
    # label_result = label_result["output"] if "output" in label_result else {}

    # prediction
    predict_tool_name = pred_tool_result["name"] if "name" in pred_tool_result else ""
    predict_result = pred_tool_result["output"] if "output" in pred_tool_result else {}
    predict_status_code = predict_result["status_code"] if "status_code" in predict_result else 500
    tool_consistency = False
    output_consistency = False
    
    # Direct match
    if label_tool_name == predict_tool_name:
        tool_consistency = True
    
    # Check similar tools
    # print("similar_tools: ", similar_tools)
    for similar_tool in similar_tools:
        if predict_tool_name == similar_tool.get("name", ""):
            tool_consistency = True

    result_success_label_list = base_error_analysis([predict_result])["result_success_label_list"]
    if sum(result_success_label_list)==len(result_success_label_list):
        output_consistency = True
    else:
        output_consistency = False
    return tool_consistency, output_consistency

def check_multi_tool_call_dag(pred_tool_result_list: List[Dict], label_result_list: List[Dict]) -> Tuple[bool, bool]:
    """
    Check the correctness of tool calls for DAG structure
    
    Args:
        pred_tool_result_list: List of predicted tool call results
        label_result_list: List of ground truth tool call results
        
    Returns:
        Tuple[bool, bool]: (tool_consistency, output_consistency)
    """
    
    def get_leaf_nodes(tool_list: List[Dict]) -> List[Dict]:
        """
        Get leaf nodes (last tool calls) from tool list
        If the last tool name is repeated, get all consecutive calls with the same name
        """
        if not tool_list:
            return []
        
        leaf_nodes = []
        last_tool_name = tool_list[-1]["name"]
        
        # Iterate from the end to find all consecutive calls with the same tool name
        for i in range(len(tool_list) - 1, -1, -1):
            if tool_list[i]["name"] == last_tool_name:
                leaf_nodes.insert(0, tool_list[i])
            else:
                break
                
        return leaf_nodes
    
    if len(label_result_list)<1 or len(pred_tool_result_list)<1:
        return False, False
    # Get leaf nodes from both lists
    # pred_leaf_nodes = get_leaf_nodes(pred_tool_result_list)
    # label_leaf_nodes = get_leaf_nodes(label_result_list)
    pred_leaf_nodes = pred_tool_result_list[-1]
    label_leaf_nodes = label_result_list[-1]
    # print("[debug] pred_leaf_nodes:", pred_leaf_nodes)
    # print("[debug] label_leaf_nodes:", label_leaf_nodes)
    
    return check_single_tool_call_dag(pred_leaf_nodes, label_leaf_nodes)

if __name__ == "__main__":
    # Read the input JSON file
    input_file_path = "logs/browser/browser_0711_single_500_20250713_080044.json"
    output_file_path = "logs/browser/browser_0711_single_500_20250713_080044_ast.json"
    # input_file_path = "logs/browser/test_log.json"
    # output_file_path = "logs/browser/test_log_ast.json"
    
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Calculate total number of function calls to process
        total_function_calls = 0
        for run_detail in data.get("run_details", []):
            for trial in run_detail.get("trials", []):
                total_function_calls += len(trial.get("function_call_result", []))
        
        print(f"Total function calls to process: {total_function_calls}")
        
        # Process each run_detail with progress bar
        processed_calls = 0
        for run_detail in tqdm(data.get("run_details", []), desc="Processing run_details"):
            function_call_label = run_detail.get("function_call_label", [])
            query = run_detail.get("query", [])
            
            # Process each trial
            for trial in run_detail.get("trials", []):
                function_call_results = trial.get("function_call_result", [])
                
                # Call check_ast with function_call_label and function_call_result
                tool_correctness, parameter_correctness, _judge_usage = check_ast(
                    function_call_results,
                    function_call_label,
                    query
                )
                
                # Add the new fields to function_call_result
                trial["tool_correctness"] = True if tool_correctness == 1 else False
                trial["parameter_correctness"] = True if parameter_correctness == 1 else False
                
                processed_calls += 1
        
        # Write the output file
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Processing completed. Output written to {output_file_path}")
        
    except FileNotFoundError:
        print(f"Error: Input file {input_file_path} not found")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}")
    except Exception as e:
        print(f"Error: {e}")
