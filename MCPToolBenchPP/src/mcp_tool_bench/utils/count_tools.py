import os
import json
import re
from pathlib import Path

from shared_format import count_tokens as _shared_count_tokens

def count_mcp_files(directory):
    """Count MCP files excluding jsonl and type_tools.json files"""
    count = 0
    for file in os.listdir(directory):
        if file.endswith('.json') and not file.endswith('_tools.json'):
            count += 1
    return count

def count_words(text):
    """Count words in text by splitting on whitespace and special characters"""
    # Remove special characters and split on whitespace
    words = re.findall(r'\b\w+\b', text.lower())
    return len(words)

def count_tokens(text):
    """Count tokens using shared_format's canonical tiktoken cl100k_base counter."""
    return _shared_count_tokens(text)

def count_tools(mcp_type_dir):
    base_dir = mcp_type_dir
    results = []
    
    # Process each subdirectory
    for subdir in os.listdir(base_dir):
        subdir_path = os.path.join(base_dir, subdir)
        if not os.path.isdir(subdir_path):
            continue
            
        # Find the type_tools.json file
        tools_file = os.path.join(subdir_path, f'{subdir}_tools.json')
        if not os.path.exists(tools_file):
            print(f"Warning: {tools_file} not found")
            continue
            
        # Count total tools and calculate statistics
        with open(tools_file, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
            # tools = data.get('tools', [])
            tools = data
            total_tools = len(tools)
            
            # Calculate statistics for all tools
            char_lengths = []
            word_counts = []
            token_counts = []
            
            for tool in tools:
                tool_str = json.dumps(tool)
                char_lengths.append(len(tool_str.encode('utf-8')))
                word_counts.append(count_words(tool_str))
                token_counts.append(count_tokens(tool_str))
            
            total_chars = sum(char_lengths)
            total_words = sum(word_counts)
            total_tokens = sum(token_counts)
            
            avg_chars = total_chars / total_tools if total_tools > 0 else 0
            avg_words = total_words / total_tools if total_tools > 0 else 0
            avg_tokens = total_tokens / total_tools if total_tools > 0 else 0
            
            max_chars = max(char_lengths) if char_lengths else 0
            min_chars = min(char_lengths) if char_lengths else 0
            max_words = max(word_counts) if word_counts else 0
            min_words = min(word_counts) if word_counts else 0
            max_tokens = max(token_counts) if token_counts else 0
            min_tokens = min(token_counts) if token_counts else 0
            
        # Count MCP files
        mcp_count = count_mcp_files(subdir_path)
        
        # Calculate average
        avg_tools = total_tools / mcp_count if mcp_count > 0 else 0
        
        results.append({
            'type': subdir,
            'total_tools': total_tools,
            'mcp_count': mcp_count,
            'avg_tools_per_mcp': round(avg_tools, 2),
            'avg_chars_per_tool': round(avg_chars, 2),
            'avg_words_per_tool': round(avg_words, 2),
            'avg_tokens_per_tool': round(avg_tokens, 2),
            'max_chars': max_chars,
            'min_chars': min_chars,
            'max_words': max_words,
            'min_words': min_words,
            'max_tokens': max_tokens,
            'min_tokens': min_tokens,
            'total_chars': total_chars,
            'total_words': total_words,
            'total_tokens': total_tokens
        })
    
    # Sort results by total tools
    results.sort(key=lambda x: x['total_tools'], reverse=True)
    
    # Prepare output string
    output = []
    output.append("\n{:<30} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15}".format(
        "Type", "Total Tools", "MCP Count", "Avg Tools/MCP", "Avg Chars/Tool", "Avg Words/Tool", 
        "Avg Tokens/Tool", "Tool Max Chars", "Tool Min Chars", "Tool Max Words", "Tool Min Words", 
        "Tool Max Tokens", "Tool Min Tokens"))
    output.append("-" * 195)
    
    for r in results:
        output.append("{:<30} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15} {:<15}".format(
            r['type'],
            r['total_tools'],
            r['mcp_count'],
            r['avg_tools_per_mcp'],
            r['avg_chars_per_tool'],
            r['avg_words_per_tool'],
            r['avg_tokens_per_tool'],
            r['max_chars'],
            r['min_chars'],
            r['max_words'],
            r['min_words'],
            r['max_tokens'],
            r['min_tokens']
        ))
    
    # Print to console
    print("\n".join(output))
    
    # Write to file
    mcp_type_dir = Path(mcp_type_dir)
    with open(mcp_type_dir.parent / "logs" / "tools_statistics.txt", 'w', encoding='utf-8-sig') as f:
        f.write("\n".join(output))
        f.write("\n\nSummary Statistics:\n")
        f.write("-" * 50 + "\n")
        f.write(f"Total Types: {len(results)}\n")
        f.write(f"Total Tools Across All Types: {sum(r['total_tools'] for r in results)}\n")
        f.write(f"Total MCPs Across All Types: {sum(r['mcp_count'] for r in results)}\n")
        f.write(f"Overall Average Tools per MCP: {sum(r['total_tools'] for r in results) / sum(r['mcp_count'] for r in results):.2f}\n")
        f.write(f"Overall Average Chars per Tool: {sum(r['total_tools'] * r['avg_chars_per_tool'] for r in results) / sum(r['total_tools'] for r in results):.2f}\n")
        f.write(f"Overall Average Words per Tool: {sum(r['total_tools'] * r['avg_words_per_tool'] for r in results) / sum(r['total_tools'] for r in results):.2f}\n")
        f.write(f"Overall Average Tokens per Tool: {sum(r['total_tools'] * r['avg_tokens_per_tool'] for r in results) / sum(r['total_tools'] for r in results):.2f}\n")
        f.write(f"Global Max Chars: {max(r['max_chars'] for r in results)}\n")
        f.write(f"Global Min Chars: {min(r['min_chars'] for r in results)}\n")
        f.write(f"Global Max Words: {max(r['max_words'] for r in results)}\n")
        f.write(f"Global Min Words: {min(r['min_words'] for r in results)}\n")
        f.write(f"Global Max Tokens: {max(r['max_tokens'] for r in results)}\n")
        f.write(f"Global Min Tokens: {min(r['min_tokens'] for r in results)}\n")
        # f.write(f"Total Characters Across All Types: {sum(r['total_chars'] for r in results)}\n")
        # f.write(f"Total Words Across All Types: {sum(r['total_words'] for r in results)}\n")
        # f.write(f"Total Tokens Across All Types: {sum(r['total_tokens'] for r in results)}\n")

if __name__ == '__main__':
    mcp_type_dir = "mcp/tools"
    count_tools(mcp_type_dir) 
