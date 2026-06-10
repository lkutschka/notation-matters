'''
Post-process user questions and tool call examples to remove unreasonable data.
'''

import json
from typing import List, Dict, Any
import csv
import json
import random
import re
import ast
import os
from typing import Dict, List, Tuple
import logging
import sys
import html
from bs4 import BeautifulSoup
import re
from tqdm import tqdm
import copy
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, '../../..')))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, '../..')))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, '../')))
sys.path.insert(0, os.path.abspath(os.path.join(CURRENT_DIR, './')))
from src.mcp_tool_bench.model_utils.model_provider import _global_model_provider
from src.mcp_tool_bench.global_variables import *
from utils.prompt import user_prompt_template_reasonableness_checks, system_prompt_template_reasonableness_checks
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def post_process_data(generated_data: List[Dict], fill_iterations: int = 1, category: str = "demo", category_tools_path: str = "mcp/tools/demo/demo_tools.json") -> List[Dict]:
    """
    Post-process generated data to remove unreasonable data
    
    Args:
        generated_data: Original generated data list
        fill_iterations: Number of times to fill variables randomly
        category: Data category
        category_tools_path: MCP tools path
        
    Returns:
        List[Dict]: Processed data list
    """
    processed_data = []
    existing_queries = set()  # Track existing queries to avoid duplicates
    
    # Add progress bar for processing generated data
    for item in tqdm(generated_data, desc="Post-processing data", unit="item"):
        # Fill variables in the data
        filled_items = fill_variables_in_data(item, fill_iterations)

        # Process each filled item
        for filled_item in filled_items:
            # # Check data integrity
            if not is_valid_data(filled_item):
                continue
            # Clean and standardize data
            cleaned_item = clean_data(filled_item)
            
            # Check if query already exists in processed_data
            query = cleaned_item.get('query', '').strip()
            if query in existing_queries:
                continue  # Skip if query already exists
            
            # Validate data reasonableness
            is_reasonable, rewritten_query = is_reasonable_data(cleaned_item)
            # print("[DEBUG] query: ", query, "rewritten_query: ", rewritten_query, "is_reasonable: ", is_reasonable)
            if is_reasonable:
                # Add similar tools for each tool in function_call_label
                cleaned_item = add_similar_tools(cleaned_item, category)
                cleaned_item['query'] = rewritten_query
                processed_data.append(cleaned_item)
                existing_queries.add(query)  # Add to existing queries set
    
    print(f"Post-processing completed: {len(generated_data)} original items, {len(processed_data)} after processing")
    return processed_data

def contains_special_chars(value):
    """check if value contains < or >"""
    if isinstance(value, str):
        return '<' in value or '>' in value or '{' in value or '}' in value
    elif isinstance(value, list):
        return any(contains_special_chars(item) for item in value)
    elif isinstance(value, dict):
        return any(contains_special_chars(v) for v in value.values())
    return False

def is_valid_data(item: Dict) -> bool:
    """
    Check if data is complete and valid
    
    Args:
        item: Data item
        
    Returns:
        bool: Whether it is valid
    """
    # Check if required fields exist
    required_fields = ['query', 'function_call_label']
    for field in required_fields:
        if field not in item or not item[field]:
            print(f"Missing required field: {field}")
            return False
    # check < or > in input
    if contains_special_chars(item.get('query', '')):
        print("< or > in query")
        return False
    return True

def clean_data(item: Dict) -> Dict:
    """
    Clean and standardize data
    
    Args:
        item: Original data item
        
    Returns:
        Dict: Cleaned data item
    """
    cleaned_item = item.copy()
    
    # Clean query field
    if 'query' in cleaned_item:
        cleaned_item['query'] = cleaned_item['query'].strip()
    
    # Clean function_call_label field
    if 'function_call_label' in cleaned_item:
        # TODO: Implement function_call_label cleaning logic
        pass
    
    return cleaned_item


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

def is_reasonable_data(item: Dict) -> Tuple[bool, str]:
    """
    Validate if data is reasonable
    
    Args:
        item: Data item
        
    Returns:
        bool: Whether it is reasonable
    """
    # Check query length, Check if function_call_label is empty
    if len(item.get('query', '')) < 5 or len(item.get('function_call_label', [])) < 1:
        return False
    
    # TODO: Add more reasonableness check logic
    user_prompt = user_prompt_template_reasonableness_checks.format(query=item.get('query', ''), function_call_label=item.get('function_call_label', []))
    system_prompt = system_prompt_template_reasonableness_checks.format()
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
    raw_response = output[KEY_COMPLETION] if KEY_COMPLETION in output else ""

    if isinstance(raw_response, str):
        result =  process_response(raw_response)

    # print("result: ", result)
    # print("type(result): ", type(result))

    try:
        result = json.loads(result)
        if result.get('reasonableness_checks', '0') == '1':
            return True, result.get('query_rewritten', '')
        else:
            return False, result.get('query_rewritten', '')
    except Exception as e:
        # logger.error(f"Error processing response: {e}")
        return False, item.get('query', '')

def add_similar_tools(item: Dict, category: str) -> Dict:
    """
    Add similar tools for each tool in function_call_label
    
    Args:
        item: Data item
        category: Data category (demo, browser, etc.)
        
    Returns:
        Dict: Data item with similar_tools field added
    """
    import importlib.util
    import os
    
    # Construct path to similar_tools.py file
    similar_tools_path = f"mcp/tools/{category}/similar_tools.py"
    
    # Check if similar_tools.py exists
    if not os.path.exists(similar_tools_path):
        logger.warning(f"similar_tools.py not found at {similar_tools_path}")
        return item
    
    try:
        # Import similar_tools module
        spec = importlib.util.spec_from_file_location("similar_tools", similar_tools_path)
        similar_tools_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(similar_tools_module)
        
        similar_tools_dict = similar_tools_module.similar_tools_dict
        
        # Process each tool in function_call_label
        if 'function_call_label' in item:
            for tool in item['function_call_label']:
                tool_name = tool.get('name', '')
                tool_mcp_server = tool.get('mcp_server', '')
                
                # Find similar tools
                similar_tools = find_similar_tools(tool_name, tool_mcp_server, similar_tools_dict)
                tool['similar_tools'] = similar_tools
                
    except Exception as e:
        logger.error(f"Error loading similar_tools.py: {e}")
    
    return item


def find_similar_tools(tool_name: str, tool_mcp_server: str, similar_tools_dict: Dict) -> List[Dict]:
    """
    Find similar tools for a given tool
    
    Args:
        tool_name: Name of the tool
        tool_mcp_server: MCP server of the tool
        similar_tools_dict: Dictionary of similar tools categories
        
    Returns:
        List[Dict]: List of similar tools with name and mcp_server
    """
    similar_tools = []
    
    # Iterate through all categories in similar_tools_dict
    for category_name, category_data in similar_tools_dict.items():
        tools_in_category = category_data.get('tools', [])
        
        # Check if current tool is in this category
        current_tool_in_category = False
        for tool_info in tools_in_category:
            if tool_info.get('name') == tool_name and tool_info.get('mcp_server') == tool_mcp_server:
                current_tool_in_category = True
                break
        
        # If current tool is in this category, add all other tools in the same category
        if current_tool_in_category:
            for tool_info in tools_in_category:
                # Skip the current tool itself
                if tool_info.get('name') == tool_name and tool_info.get('mcp_server') == tool_mcp_server:
                    continue
                
                # Add similar tool
                similar_tools.append({
                    "name": tool_info.get('name', ''),
                    "mcp_server": tool_info.get('mcp_server', '')
                })
    
    return similar_tools




def fill_variables_in_data(item: Dict, num_iterations: int = 1) -> List[Dict]:
    """
    Fill variables in query and function_call_label with random values from variable_optional_collection
    
    Args:
        item: Original data item
        num_iterations: Number of times to fill variables randomly
        
    Returns:
        List[Dict]: List of filled data items
    """
    filled_items = []
    
    # Extract variables from query
    query = item.get('query', '')
    variables = extract_variables(query)
    
    # Get variable collection
    variable_collection = item.get('variable_optional_collection', [])
    
    if len(variable_collection) > 0:
        # Generate num_iterations filled items
        for iteration in range(num_iterations):
            filled_item = item.copy()
            # Fill query variables
            filled_query, filled_values = fill_query(query, variables, variable_collection)
            filled_item['query'] = filled_query
            
            # Fill function_call_label variables
            if 'function_call_label' in filled_item:
                # deep copy function_call_label, avoid multiple filling pollution
                filled_item['function_call_label'] = copy.deepcopy(item['function_call_label'])
                filled_function_calls = fill_function_calls(filled_item['function_call_label'], filled_values)
                filled_item['function_call_label'] = filled_function_calls
            
            # Remove variable_optional_collection field after filling
            filled_item.pop('variable_optional_collection', None)
            
            filled_items.append(filled_item)
    return filled_items


def extract_variables(query: str) -> List[str]:
    """Extract all variable names from query"""
    return re.findall(r'<([^>]+)>', query)


def get_random_values(variable: str, collection: Dict) -> List:
    """Get candidate values for variable from collection"""
    if variable not in collection:
        # Provide default values for common variables
        default_values = {
            'location': ['beijing', 'shanghai', 'guangzhou', 'shenzhen', 'hangzhou'],
            'address': ['beijing', 'shanghai', 'guangzhou', 'shenzhen', 'hangzhou'],
            'coordinates': ['116.404,39.915', '121.473,31.230', '113.264,23.129', '114.057,22.543', '120.155,30.274'],
            'city': ['beijing', 'shanghai', 'guangzhou', 'shenzhen', 'hangzhou'],
            'keyword': ['restaurant', 'cafe', 'hotel', 'mall', 'park'],
            'radius': ['1000', '2000', '3000', '5000'],
            'ip': ['192.168.1.1', '10.0.0.1', '172.16.0.1'],
            'id': ['12345', '67890', '54321'],
            'name': ['zhangsan', 'lisi', 'wangwu'],
            'time': ['2024-03-20 10:00', '2024-03-20 14:30', '2024-03-20 18:00']
        }
        return default_values.get(variable, [f"<{variable}>"])
    return collection[variable]


def fill_query(query: str, variables: List[str], collection: List[Dict]) -> Tuple[str, Dict[str, str]]:
    """Fill variables in query with random values and return filled query and variable mapping"""
    filled_query = query
    filled_values = random.choice(collection)  # Store filled values for each variable
    
    for var in variables:
        if var not in filled_values:
            continue
        value = filled_values[var]
        value_str = str(value)  # Convert to string
        # Replace variable with filled value
        filled_query = filled_query.replace(f"<{var}>", value_str)
    
    return filled_query, filled_values


def extract_variables_from_function_calls(function_calls: List) -> List[str]:
    """extract all variables from function_calls"""
    variables = []
    for call in function_calls:
        if 'arguments' in call:
            for key, value in call['arguments'].items():
                if isinstance(value, str):
                    # extract variables from string
                    vars_in_str = re.findall(r'\{([^}]+)\}', value)
                    variables.extend(vars_in_str)
                elif isinstance(value, dict):
                    # recursively process nested dictionary
                    for k, v in value.items():
                        if isinstance(v, str):
                            vars_in_str = re.findall(r'\{([^}]+)\}', v)
                            variables.extend(vars_in_str)
    return list(set(variables))  # remove duplicates

def fill_function_calls(function_calls: List, filled_values: Dict[str, str]) -> List:
    """Fill variables in function_calls"""
    filled_calls = []
    for call in function_calls:
        filled_call = call.copy()
        
        if 'arguments' in filled_call:
            for key, value in filled_call['arguments'].items():
                if isinstance(value, str):
                    # Fill variables in string - check for both <var> and {var} formats
                    for var_name, filled_value in filled_values.items():
                        if not isinstance(filled_value, str):
                            continue
                        # Check for <var> format
                        if f"<{var_name}>" in value:
                            try:
                                filled_call['arguments'][key] = value.replace(f"<{var_name}>", filled_value)
                            except Exception as e:
                                print(f"Error filling variable {var_name} in string: {e}")
                        # Check for {var} format
                        elif f"{{{var_name}}}" in value:
                            try:
                                filled_call['arguments'][key] = value.replace(f"{{{var_name}}}", filled_value)
                            except Exception as e:
                                print(f"Error filling variable {var_name} in string: {e}")
                elif isinstance(value, list) or isinstance(value, dict):
                    for var_name, filled_value in filled_values.items():
                        try:
                            value = ast.literal_eval(str(value).replace(f"<{var_name}>", str(filled_value)).replace(f"{{{var_name}}}", str(filled_value)))
                        except Exception as e:
                            print(f"Error filling variable {var_name} in list or dict: {e}")
                    filled_call['arguments'][key] = value

        filled_calls.append(filled_call)
    
    return filled_calls


if __name__ == "__main__":
    test_data = [
        {
            "query": "Capture a screenshot of the element <query_element> on the page with the name <query_screenshot_name>.",
            "function_call_label": [
            {
                "name": "puppeteer_screenshot",
                "arguments": {
                "name": "<query_screenshot_name>",
                "selector": "<query_element>"
                },
                "step": "1",
                "id": "1",
                "mcp_server": "puppeteer/puppeteer"
            }
            ],
            "variable_optional_collection": {
            "query_element": [
                "#header",
                ".main-content",
                "#footer",
                ".sidebar",
                "#hero-image"
            ],
            "query_screenshot_name": [
                "HomePageHeader",
                "ContentSection",
                "FooterCapture",
                "SidebarSnapshot",
                "HeroImageScreenshot"
            ]
            }
        },
        {
            "query": "Navigate to the website <url> and take a screenshot.",
            "function_call_label": [
            {
                "name": "playwright_navigate",
                "arguments": {
                "url": "<url>"
                },
                "step": "1",
                "id": "1",
                "mcp_server": "executeautomation/mcp-playwright"
            }
            ],
            "variable_optional_collection": {
            "url": [
                "https://www.google.com",
                "https://www.github.com",
                "https://www.stackoverflow.com"
            ]
            }
        }
    ]
    
    # Test the variable filling functionality
    print("Testing variable filling functionality...")
    print(f"Input data count: {len(test_data)}")
    
    # Test with 3 iterations
    result = post_process_data(test_data, fill_iterations=3)
    
    print(f"Output data count: {len(result)}")
    print("\nSample filled data:")
    for i, item in enumerate(result[:3]):  # Show first 3 items
        print(f"\nItem {i+1}:")
        print(f"Query: {item.get('query', '')}")
        print(f"Function call: {item.get('function_call_label', '')}")
        
        # Show similar tools for each function call
        for j, func_call in enumerate(item.get('function_call_label', [])):
            if 'similar_tools' in func_call:
                print(f"  Function {j+1} similar tools: {func_call['similar_tools']}")
