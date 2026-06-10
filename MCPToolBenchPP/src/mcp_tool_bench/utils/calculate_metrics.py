#!/usr/bin/env python3
"""
Script to calculate tool_pass@{k} and parameter_pass@{k} metrics from existing log files.
This script can process log files that contain tool_correctness and parameter_correctness data
but don't have the calculated pass@k metrics for these dimensions.
"""

import json
import argparse
import os
import numpy as np
from typing import List, Dict, Any, Tuple
from src.mcp_tool_bench.evaluation.evaluation_utils import estimate_pass_at_k, base_error_analysis

def check_single_tool_call_dag(pred_tool_result: Dict, label_result: Dict) -> Tuple[bool, bool]:
    # implementation
    label_tool_name = label_result["name"] if "name" in label_result else ""
    label_result = label_result["output"] if "output" in label_result else {}

    # prediction
    predict_tool_name = pred_tool_result["name"] if "name" in pred_tool_result else ""
    predict_result = pred_tool_result["output"] if "output" in pred_tool_result else {}
    predict_status_code = predict_result["status_code"] if "status_code" in predict_result else 500

    if label_tool_name == predict_tool_name:
        tool_consistency = True
    else:
        tool_consistency = False

    result_success_label_list = base_error_analysis([predict_result])["result_success_label_list"]
    if sum(result_success_label_list)==len(result_success_label_list):
        output_consistency = True
    else:
        output_consistency = False
    return tool_consistency, output_consistency

def check_correctness(pred_tool_result_list: List[Dict], label_result_list: List[Dict]) -> Tuple[bool, bool]:
    """
    Check the correctness of tool calls
    
    Args:
        pred_tool_result_list: Tool call prediction result list
        label_result_list: Tool call ground truth result list

    Returns:
        Tuple[bool, bool]: (tool_consistency, output_consistency)
    """
    label_step = len(label_result_list) if label_result_list is not None else 0
    predict_step = len(pred_tool_result_list) if pred_tool_result_list is not None else 0

    tool_consistency = False
    output_consistency = False
    
    label_result = label_result_list[-1]
    pred_tool_result = pred_tool_result_list[-1]
    tool_consistency, output_consistency = check_single_tool_call_dag(pred_tool_result, label_result)
    
    return tool_consistency, output_consistency

def calculate_metrics_from_log(log_file_path: str, pass_k_list: List[int] = None) -> Dict[str, Any]:
    """
    Calculate tool_pass@{k} and parameter_pass@{k} metrics from a log file.
    
    Args:
        log_file_path: Path to the log file
        pass_k_list: List of k values for pass@k calculation. If None, will extract from log file.
        
    Returns:
        Dict containing the calculated metrics
    """
    
    # Load log file
    with open(log_file_path, 'r', encoding='utf-8') as f:
        log_data = json.load(f)
    
    # Extract pass_k_list from log if not provided
    if pass_k_list is None:
        pass_k_str = log_data.get("run_info", {}).get("pass_k", "1")
        pass_k_list = [int(k) for k in pass_k_str.split(",")]
    
    print(f"Processing log file: {log_file_path}")
    print(f"Pass@k values: {pass_k_list}")
    
    # Extract run details
    run_details = log_data.get("run_details", [])
    if not run_details:
        print("No run_details found in log file")
        return {}
    
    # Arrays to store results for each task
    num_trails_array = []
    num_pass_array = []
    num_tool_correct_array = []
    num_parameter_correct_array = []
    
    run_details = run_details[:50]
    # Process each task
    for task in run_details:
        trials = task.get("trials", [])
        if not trials:
            continue
            
        # Count trials and correct results
        num_trials = len(trials)
        num_passed = 0
        num_tool_correct = 0
        num_parameter_correct = 0

        # Calculate directly from log
        num_passed = sum(1 for trial in trials if (trial.get("if_pass", False) and trial.get("tool_correctness", False) and trial.get("parameter_correctness", False)))
        num_tool_correct = sum(1 for trial in trials if trial.get("tool_correctness", False))
        num_parameter_correct = sum(1 for trial in trials if (trial.get("parameter_correctness", False) and trial.get("tool_correctness", False)))
        
        num_trails_array.append(num_trials)
        num_pass_array.append(num_passed)
        num_tool_correct_array.append(num_tool_correct)
        num_parameter_correct_array.append(num_parameter_correct)
    
    print(f"Processed {len(num_trails_array)} tasks")
    print(f"Total trials: {sum(num_trails_array)}")
    print(f"Total passed: {sum(num_pass_array)}")
    print(f"Total tool correct: {sum(num_tool_correct_array)}")
    print(f"Total parameter correct: {sum(num_parameter_correct_array)}")
    
    # Calculate metrics for each k value
    metrics_list = []
    run_info = log_data.get("run_info", {})
    
    for k in pass_k_list:
        # Calculate pass@{k} for overall correctness
        pass_at_k_arr = estimate_pass_at_k(num_trails_array, num_pass_array, k)
        pass_at_k = float(np.mean(pass_at_k_arr)) if len(pass_at_k_arr) > 0 else 0
        
        # Calculate tool_pass@{k}
        tool_pass_at_k_arr = estimate_pass_at_k(num_trails_array, num_tool_correct_array, k)
        tool_pass_at_k = float(np.mean(tool_pass_at_k_arr)) if len(tool_pass_at_k_arr) > 0 else 0
        
        # Calculate parameter_pass@{k}
        parameter_pass_at_k_arr = estimate_pass_at_k(num_trails_array, num_parameter_correct_array, k)
        parameter_pass_at_k = float(np.mean(parameter_pass_at_k_arr)) if len(parameter_pass_at_k_arr) > 0 else 0
        
        metric = {
            "category": run_info.get("category", "unknown"),
            "model": run_info.get("model", "unknown"),
            f"pass@{k}": pass_at_k,
            f"tool_pass@{k}": tool_pass_at_k,
            f"parameter_pass@{k}": parameter_pass_at_k,
            "num_tasks": len(num_trails_array),
            "num_trials_total": sum(num_trails_array),
            "num_passed_total": sum(num_pass_array),
            "num_tool_correct_total": sum(num_tool_correct_array),
            "num_parameter_correct_total": sum(num_parameter_correct_array)
        }
        metrics_list.append(metric)
        
        print(f"Pass@{k} - Tool_selected: {tool_pass_at_k:.4f}, Parameter: {parameter_pass_at_k:.4f}, Tool_call: {pass_at_k:.4f}")
    
    return {
        "run_info": run_info,
        "metrics": metrics_list,
        "calculation_info": {
            "log_file": log_file_path,
            "pass_k_list": pass_k_list,
            "num_tasks": len(num_trails_array),
            "total_trials": sum(num_trails_array)
        }
    }


def update_log_file_with_metrics(log_file_path: str, output_file_path: str = None) -> str:
    """
    Update the original log file with the calculated metrics.
    
    Args:
        log_file_path: Path to the original log file
        output_file_path: Path for the updated log file. If None, will overwrite original.
        
    Returns:
        Path to the updated log file
    """
    
    # Calculate metrics
    result = calculate_metrics_from_log(log_file_path)
    
    if not result:
        print("Failed to calculate metrics")
        return ""
    
    # Load original log file
    with open(log_file_path, 'r', encoding='utf-8') as f:
        original_log = json.load(f)
    
    # Update metrics in the original log
    original_log["metrics"] = result["metrics"]
    
    # Determine output file path
    if output_file_path is None:
        output_file_path = log_file_path
    
    # Save updated log file
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(original_log, f, ensure_ascii=False, indent=2)
    
    print(f"Updated log file saved to: {output_file_path}")
    return output_file_path


def process_multiple_logs(log_dir: str, pattern: str = None) -> None:
    """
    Process multiple log files in a directory.
    
    Args:
        log_dir: Directory containing log files
        pattern: Optional pattern to filter log files (e.g., "browser_0711_single_500")
    """
    
    if not os.path.exists(log_dir):
        print(f"Directory not found: {log_dir}")
        return
    
    log_files = []
    for file in os.listdir(log_dir):
        if file.endswith('.json'):
            if pattern is None or pattern in file:
                log_files.append(os.path.join(log_dir, file))
    
    print(f"Found {len(log_files)} log files to process")
    
    for log_file in log_files:
        print(f"\nProcessing: {log_file}")
        try:
            update_log_file_with_metrics(log_file)
        except Exception as e:
            print(f"Error processing {log_file}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Calculate tool_pass@{k} and parameter_pass@{k} metrics from log files")
    parser.add_argument("--log_file", type=str, help="Path to a single log file")
    parser.add_argument("--log_dir", type=str, help="Directory containing log files")
    parser.add_argument("--pattern", type=str, help="Pattern to filter log files (when using --log_dir)")
    parser.add_argument("--pass_k", type=str, default="1,3", help="Comma-separated list of k values for pass@k")
    parser.add_argument("--output", type=str, help="Output file path (for single file processing)")
    parser.add_argument("--calculate_only", action="store_true", help="Only calculate and display metrics, don't update log file")
    
    args = parser.parse_args()
    
    pass_k_list = [int(k) for k in args.pass_k.split(",")]
    
    if args.log_file:
        if args.calculate_only:
            # Only calculate and display metrics
            result = calculate_metrics_from_log(args.log_file, pass_k_list)
            if result:
                print("\nCalculated Metrics:")
                for metric in result["metrics"]:
                    print(f"  {metric}")
        else:
            # Update log file with metrics
            update_log_file_with_metrics(args.log_file, args.output)
    
    elif args.log_dir:
        # Process multiple log files
        process_multiple_logs(args.log_dir, args.pattern)
    
    else:
        print("Please provide either --log_file or --log_dir")
        parser.print_help()

if __name__ == "__main__":
    main() 
