'''
Randomly extract tools from category_tools.json, perform multiple extractions and generate extraction result files, placed in logs directory
'''

import json
import random
from pathlib import Path
from typing import List, Dict, Any


def merge_mcp_tools(category: str, mcp_config_path: str) -> str:
    """
    Merge all MCP tools in the specified category directory
    
    Args:
        category: Data category, such as browser, search
        mcp_config_path: MCP configuration file path
        
    Returns:
        str: Path to the merged tools file
    """
    # Build category directory path
    category_dir = Path(f"mcp/tools/{category}")
    
    if not category_dir.exists():
        raise FileNotFoundError(f"Category directory does not exist: {category_dir}")
    
    output_file = category_dir / f"{category}_tools.json"
    
    # # Check if merged file already exists
    # if output_file.exists():
    #     print(f"Merged file already exists, skipping merge step: {output_file}")
    #     return str(output_file)
    
    # Collect all MCP tools
    all_tools = []
    
    # Iterate through all JSON files in the directory
    for json_file in category_dir.glob("*.json"):
        if json_file.name == f"{category}_tools.json":
            continue  # Skip existing merged file
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                mcp_data = json.load(f)
            
            # Extract MCP ID from file content
            mcp_id = mcp_data.get('server_name', json_file.stem)  # Fallback to filename if no id field
            
            # Extract tools field
            if 'tools' in mcp_data:
                tools = mcp_data['tools']
                if isinstance(tools, list):
                    # Add mcp_server field to each tool
                    for tool in tools:
                        tool['mcp_server'] = mcp_id
                    all_tools.extend(tools)
                else:
                    # Add mcp_server field to single tool
                    tools['mcp_server'] = mcp_id
                    all_tools.append(tools)
                    
        except Exception as e:
            print(f"Warning: Cannot read file {json_file}: {e}")
            continue
    
    # Remove duplicate tools (based on tool name AND mcp_server)
    # Keep tools with same name but from different MCP servers
    unique_tools = []
    tool_key_set = set()  # Track (tool_name, mcp_server) combinations
    # Generate mcp_tools_dict: {mcp_server: [tool_name1, tool_name2, ...]}
    # Handle tool name conflicts by renaming to "mcp_server_tool_name" format
    # First occurrence keeps original name, subsequent conflicts get renamed
    mcp_tools_dict = {}
    all_tool_names = set()  # Track all tool names across all MCP servers
    
    for tool in all_tools:
        tool_name = tool.get('name', '')
        mcp_server = tool.get('mcp_server', 'unknown')
        
        if tool_name:
            tool_key = (tool_name, mcp_server)
            if tool_key not in tool_key_set:
                tool_key_set.add(tool_key)

                # Check if tool name already exists in any MCP server
                if tool_name in all_tool_names:
                    # Rename to avoid conflict: "mcp_server_tool_name"
                    new_tool_name = f"{mcp_server}_{tool_name}"
                    tool['name'] = new_tool_name  # Update the tool name in the original list
                else:
                    new_tool_name = tool_name
                    
                # Add to tracking set (use the new name for future conflict detection)
                all_tool_names.add(new_tool_name)
                
                # Add to mcp_tools_dict
                if mcp_server not in mcp_tools_dict:
                    mcp_tools_dict[mcp_server] = []
                mcp_tools_dict[mcp_server].append(new_tool_name)

                unique_tools.append(tool)
    
    # Save merged tools file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_tools, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully merged {len(unique_tools)} tools to: {output_file}")
    return str(output_file), mcp_tools_dict

def random_extract_tools(category_tools_path: str, num_extractions: int = 10, 
                        min_tools: int = 1, max_tools: int = 3) -> List[List[Dict]]:
    """
    Randomly extract tools from category tools file
    
    Args:
        category_tools_path: Category tools file path
        num_extractions: Number of extractions
        min_tools: Minimum number of tools per extraction
        max_tools: Maximum number of tools per extraction
        
    Returns:
        List[List[Dict]]: Extraction result list, each element is a group of tools
    """
    # Read all tools
    with open(category_tools_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    # Handle different data structures
    if isinstance(data, dict) and 'tools' in data:
        all_tools = data['tools']
    elif isinstance(data, list):
        all_tools = data
    else:
        raise ValueError(f"Unsupported data format: {type(data)}")
    
    if not all_tools:
        raise ValueError("Tool list is empty")
    
    extraction_results = []
    
    # Perform multiple random extractions
    for i in range(num_extractions):
        # Randomly decide the number of tools for this extraction
        num_tools = random.randint(min_tools, min(max_tools, len(all_tools)))
        
        # Randomly extract tools
        selected_tools = random.sample(all_tools, num_tools)
        extraction_results.append(selected_tools)
    
    # Save extraction results to logs directory
    save_extraction_results(extraction_results, category_tools_path)
    
    print(f"Completed {num_extractions} tool extractions, {min_tools}-{max_tools} tools per extraction")
    return extraction_results


def save_extraction_results(extraction_results: List[List[Dict]], category_tools_path: str):
    """
    Save extraction results to logs directory
    
    Args:
        extraction_results: Extraction result list
        category_tools_path: Original tools file path
    """
    # Create logs directory
    logs_dir = Path("src/mcp_tool_bench/agents/data_generator_agent/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract category name from original path
    category = Path(category_tools_path).parent.name
    
    # Save extraction results
    output_file = logs_dir / f"{category}_extraction_results.json"
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        json.dump(extraction_results, f, ensure_ascii=False, indent=2)
    
    print(f"Extraction results saved to: {output_file}")
