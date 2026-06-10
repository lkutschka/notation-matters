'''
This file performs the following operations:
1. Extract tools field from all mcp json files in the specified category directory under mcp_marketplace, merge them into a single file, place it in the original directory as category_tools.json (check the directory, if this file already exists, no need to re-merge)
2. Randomly extract tools from category_tools.json, perform multiple extractions and generate extraction result files, placed in logs directory
3. For each extraction result, i.e., for each tools list, call LLM to generate user questions (query field) and tool call examples list (function_call_label field). Output files are placed in logs directory
4. Post-process user questions and tool call examples to remove unreasonable data.
5. Add uuid field, category field, tools field (all tools from category_tools.json, i.e., candidate set) to the processed data, save to data/category directory, file name is category_version.json
'''

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any

from .utils.pre_process import merge_mcp_tools
from .utils.pre_process import random_extract_tools
from .utils.post_process import post_process_data
from .utils.generate_query import generate_query_and_function_calls

def run_data_generation(category: str, data_version: str, mcp_config_path: str):
    """
    Run data generation pipeline
    
    Args:
        category: Data category, such as browser, search
        data_version: Data version, such as v0, v1
        mcp_config_path: MCP configuration file path
    """
    print(f"Starting data generation: category={category}, version={data_version}")
    
    # Step 1.1: Merge MCP tools
    print("  1.1 Merge MCP tools")
    category_tools_path, mcp_tools_dict = merge_mcp_tools(category, mcp_config_path)
    
    # Step 1.2: Randomly extract tools
    print("  1.2 Randomly extract tools")
    extraction_results = random_extract_tools(category_tools_path, min_tools=2, max_tools=5, num_extractions=10)
    
    # Step 1.3: Generate user questions and tool call examples
    print("  1.3 Generate user questions and tool call examples")
    generated_data = generate_query_and_function_calls(extraction_results, category)
    
    # Step 1.4: Post-process data
    print("  1.4 Post-process data")
    processed_data = post_process_data(generated_data, fill_iterations=3, category=category, category_tools_path=category_tools_path)
    
    # Step 1.5: Save final data
    print("  1.5 Save final data")
    save_final_data(processed_data, category, data_version, category_tools_path, mcp_tools_dict)


def save_final_data(processed_data: List[Dict], category: str, data_version: str, category_tools_path: str, mcp_tools_dict: Dict):
    """
    Save final processed data
    
    Args:
        processed_data: Processed data
        category: Data category
        data_version: Data version
        category_tools_path: Category tools file path
    """
    # Read all tools as candidate set
    with open(category_tools_path, 'r', encoding='utf-8-sig') as f:
        all_tools = json.load(f)

    # Remove mcp_server field from all_tools for the final data
    cleaned_tools = []
    for tool in all_tools:
        tool_copy = tool.copy()
        tool_copy.pop('mcp_server', None)  # Remove mcp_server field
        cleaned_tools.append(tool_copy)

    # Add necessary fields to each data item
    final_data = []
    function_call_label_output = {
        "status_code": 200,
        "result": {}
    }
    for item in processed_data:
        # Determine type based on function_call_label length
        function_call_label = item.get('function_call_label', [])
        if isinstance(function_call_label, list):
            if len(function_call_label) == 1:
                item_call_type = "single"
            elif len(function_call_label) > 1:
                item_call_type = "multiple"
            else:
                item_call_type = "single"  # Default for empty list
        else:
            item_call_type = "single"  # Default for non-list or missing field
        
        # Process function_call_label: rename 'arguments' to 'input' and add 'output' field
        if isinstance(function_call_label, list):
            processed_function_call_label = []
            for call_item in function_call_label:
                if isinstance(call_item, dict):
                    processed_call_item = call_item.copy()
                    # Rename 'arguments' to 'input'
                    if 'arguments' in processed_call_item:
                        processed_call_item['input'] = processed_call_item.pop('arguments')
                    # Add 'output' field after 'input'
                    if 'input' in processed_call_item:
                        # Insert 'output' after 'input'
                        input_value = processed_call_item['input']
                        del processed_call_item['input']
                        processed_call_item['input'] = input_value
                        processed_call_item['output'] = function_call_label_output
                    else:
                        processed_call_item['output'] = function_call_label_output
                    processed_function_call_label.append(processed_call_item)
                else:
                    processed_function_call_label.append(call_item)
        else:
            processed_function_call_label = function_call_label
            
        final_item = {
            "uuid": str(uuid.uuid4()),
            "category": category,
            "call_type": item_call_type,  # Type based on function_call_label length
            "tools": cleaned_tools,  # Candidate tools set (without mcp_server field)
            "mcp_tools_dict": mcp_tools_dict,  # MCP server to tools mapping
            **item
        }
        # Update the function_call_label field with processed version
        final_item['function_call_label'] = processed_function_call_label
        final_data.append(final_item)

    # Create output directory
    output_dir = Path(f"data/{category}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save as JSON array
    output_file = output_dir / f"{category}_{data_version}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"Data saved to: {output_file}")
    print(f"Generated {len(final_data)} data items")
    print(f"MCP tools dict: {mcp_tools_dict}") 
