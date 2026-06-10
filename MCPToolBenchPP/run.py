'''
This is the entry function for starting the entire project, receiving all command line parameters
Parameters include:
--input_file: Input file path, default is data/demo/demo_v0.json
--category: Data category, such as browser, search, default is demo
--model: Model, such as GPT4o, default is GPT4o
--stage: Stage, such as demo, generation, tool_call, default is demo
--metric: Metric, such as acc, pass_k, default is pass_k
--pass_k: Parameter k, such as 1,5,10, default is 1
--agent: Execution agent, base, base_tool_rag, base_multi-agent, default is base
--mcp_config: MCP configuration file path, default is mcp_marketplace/mcp_config.json
--data_version: Data version, such as v0, v1, default is v0
--log_file: Log file name for resume functionality, optional. If not provided, auto-generates based on input file and timestamp.

stage:
1. If stage is generation, call run_data_generator.py, generate data according to specified category and data_version.
3. If stage is tool_call, call run_tool_call.py according to specified model, directly perform calling and evaluation.
4. If stage is all, first run run_data_generator.py to generate data, then call run_tool_call.py for calling and evaluation.
5. If stage is demo, use all default parameters, first run run_data_generator.py to generate data, then call run_tool_call.py for calling and evaluation.

Notes:
1. When stage is demo, all default parameters must be used, no other parameters can be specified, data will be generated first, then tool calling and evaluation will be performed.
2. When stage is generation, category and data_version must be filled, remind customers to provide all mcp tools files in the category directory under mcp_marketplace, format reference existing files.
3. When stage is tool_call, input_file, category, model must be filled
4. When stage is all, category, data_version, model must be filled, input_file is the data generated in the generation stage.
5. Print all parameters to remind users when running.
6. The tool_call stage now supports incremental logging and resume functionality. Logs are saved after each task completion, and the system can resume from where it left off if interrupted.
'''

import argparse
import sys
from pathlib import Path


from src.mcp_tool_bench import *
from src.mcp_tool_bench.format_converter import set_format_converter
from src.mcp_tool_bench.agents.data_generator_agent.run_data_generator import run_data_generation
from src.mcp_tool_bench.agents.base_tool_call_agent.run_tool_call import run_benchmark

# Default parameter values
DEFAULT_ARGS = {
    'input_file': 'data/demo/demo_v0.json',
    'category': 'demo',
    'model': 'gpt-4o',
    'stage': 'demo',
    'metric': 'pass_k',
    'pass_k': '1',
    'agent': 'base',
    'mcp_config': 'mcp_marketplace/mcp_config.json',
    'data_version': 'v0',
    'log_file': None,
    'evaluation_trial_per_task': 5,
    'llm_as_judge_model': "gpt-4o",
    'tool_format': 'json',
    'tool_call_format': None,
    'tool_mode': 'api'
}

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Project entry function')
    parser.add_argument('--input_file', default=DEFAULT_ARGS['input_file'], help='Input file path for tool_call stage, default is {}'.format(DEFAULT_ARGS['input_file']))
    parser.add_argument('--category', default=DEFAULT_ARGS['category'], help='Data category, such as browser, search, default is {}'.format(DEFAULT_ARGS['category']))
    parser.add_argument('--model', default=DEFAULT_ARGS['model'], help='Model, such as GPT4o, default is {}'.format(DEFAULT_ARGS['model']))
    parser.add_argument('--stage', default=DEFAULT_ARGS['stage'], choices=['demo', 'generation', 'tool_call', 'all'], help='Stage, such as demo, generation, tool_call, all, default is {}'.format(DEFAULT_ARGS['stage']))
    parser.add_argument('--metric', default=DEFAULT_ARGS['metric'], help='Metric, such as acc, pass_k, default is {}'.format(DEFAULT_ARGS['metric']))
    parser.add_argument('--pass_k', type=str, default=DEFAULT_ARGS['pass_k'], help='Parameter k, such as 1,5,10, default is {}'.format(DEFAULT_ARGS['pass_k']))
    parser.add_argument('--agent', default=DEFAULT_ARGS['agent'], help='Execution agent, such as base, base_tool_rag, base_multi-agent, default is {}'.format(DEFAULT_ARGS['agent']))
    parser.add_argument('--mcp_config', default=DEFAULT_ARGS['mcp_config'], help='MCP configuration file path, default is {}'.format(DEFAULT_ARGS['mcp_config']))
    parser.add_argument('--data_version', default=DEFAULT_ARGS['data_version'], help='Data version, such as v0, v1, default is {}'.format(DEFAULT_ARGS['data_version']))
    parser.add_argument('--log_file', default=DEFAULT_ARGS['log_file'], help='Specify log file name for resume functionality. If not provided, will auto-generate based on input file and timestamp.')
    parser.add_argument('--evaluation_trial_per_task', type=int, default=DEFAULT_ARGS['evaluation_trial_per_task'], help='Calculation Pass@K Number of Trials...')
    parser.add_argument('--llm_as_judge_model', type=str, default=DEFAULT_ARGS['llm_as_judge_model'], help='LLM Model Used to determine the parameters are correctly aligned with ground-truth, especial in search tool that query is rewritten')
    parser.add_argument('--tool_format', type=str, default=DEFAULT_ARGS['tool_format'], choices=['json', 'toon', 'tron'], help='Serialization format for tool schemas and results (default: json)')
    parser.add_argument('--tool_call_format', type=str, default=DEFAULT_ARGS['tool_call_format'], choices=['json', 'toon', 'tron'], help='Format for LLM tool call output (default: same as --tool_format)')
    parser.add_argument('--tool_mode', type=str, default=DEFAULT_ARGS['tool_mode'], choices=['api', 'prompt'], help='Tool calling mode: api (native OpenAI tools API) or prompt (prompt-based, required for toon/tron) (default: api)')

    return parser.parse_args()

def validate_arguments(args):
    """Validate the validity of arguments"""
    if args.stage == 'demo':
        # Check if non-default parameters are used in demo stage
        # Check if there are non-default parameters (excluding log_file which is optional)
        non_default_args = []
        for arg_name in vars(args):
            if arg_name == 'log_file':  # log_file is optional and allowed in demo
                continue
            current_value = getattr(args, arg_name)
            default_value = DEFAULT_ARGS.get(arg_name)
            if current_value != default_value:
                non_default_args.append(f"--{arg_name}")
        
        if non_default_args:
            print("Error: demo stage does not support specifying other parameters")
            print(f"Detected non-default parameters: {', '.join(non_default_args)}")
            print("demo stage will use all default parameters, please run directly: python run.py")
            return False
        
        return True
    
    if args.stage == 'generation':
        print("Note: The data generation module requires to provide all mcp tools files in the category directory under mcp_marketplace, format reference existing files.")
        if not args.category or not args.data_version:
            print("Error: generation stage must fill category, data_version")
            return False
    
    if args.stage == 'tool_call':
        if not args.input_file or not args.category or not args.model:
            print("Error: tool_call stage must fill input_file, category, model")
            return False
    
    if args.stage == 'all':
        print("Note: The data generation module requires to provide all mcp tools files in the category directory under mcp_marketplace, format reference existing files.")
        if not args.category or not args.data_version or not args.model:
            print("Error: all stage must fill category, data_version, model")
            return False
    
    return True


def print_arguments(args):
    """Print all arguments"""
    print("=== Running Parameters ===")
    for arg, value in vars(args).items():
        print(f"{arg}: {value}")
    print("===============")


def main():
    """Main function"""
    args = parse_arguments()
    print_arguments(args)

    # Validate tool_mode + tool_format combination
    if args.tool_mode == 'api' and args.tool_format != 'json':
        print(f"Error: --tool_mode api only supports --tool_format json (got '{args.tool_format}')")
        print("Use --tool_mode prompt for toon/tron formats")
        sys.exit(1)

    # Initialize format converter
    set_format_converter(args.tool_format, args.tool_mode, args.tool_call_format)

    if not validate_arguments(args):
        sys.exit(1)
    
    if args.stage == 'demo':
        # demo stage: use default parameters, generate data first, then perform tool calling and evaluation
        print("=" * 50)
        print("Executing demo stage: using default parameters")
        print("=" * 50)
        
        print("\n【Step 1】Data Generation")
        print("-" * 30)
        run_data_generation(args.category, args.data_version, args.mcp_config)
        
    elif args.stage == 'generation':
        # generation stage: generate data
        print("=" * 50)
        print("Executing generation stage: generate data")
        print("=" * 50)
        
        print("\n【Step 1】Data Generation")
        print("-" * 30)
        run_data_generation(args.category, args.data_version, args.mcp_config)
        
        print("\n" + "=" * 50)
        print("generation stage execution completed")
        print("=" * 50)
    
    elif args.stage == 'tool_call':
        # tool_call stage: tool calling and evaluation
        print("=" * 50)
        print("Executing tool_call stage: tool calling and evaluation")
        print("=" * 50)
        
        print("\n【Step 1】Tool Calling and Evaluation")
        print("-" * 30)
        run_benchmark(args)
        
        print("\n" + "=" * 50)
        print("tool_call stage execution completed")
        print("=" * 50)
    
    elif args.stage == 'all':
        # all stage: generate data first, then perform tool calling and evaluation
        print("=" * 50)
        print("Executing all stage: generate data first, then perform tool calling and evaluation")
        print("=" * 50)
        
        print("\n【Step 1】Data Generation")
        print("-" * 30)
        run_data_generation(args.category, args.data_version, args.mcp_config)
        
        print("\n【Step 2】Tool Calling and Evaluation")
        print("-" * 30)
        # Set input_file to the generated data file
        args.input_file = f"data/{args.category}/{args.category}_{args.data_version}.json"
        run_benchmark(args)
        
        print("\n" + "=" * 50)
        print("Full pipeline execution completed")
        print("=" * 50)


if __name__ == "__main__":
    main()
