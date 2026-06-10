import os
import numpy as np
from typing import Dict, List, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.mcp_tool_bench.global_variables import *

def base_error_analysis(function_call_result: Any) -> Dict[str, Any]:
    """
        prompt: 

            This is the error log. Each line separated by space include count \b reason. Please help summarize the reason into a few keywords description and calculate the count and ratio of the reason.

    """
    # function_call_result = trials[0]["function_call_result"] # list
    result_list = []
    result_success_label_list = []
    request_failed = "HTTP Request Failed..."
    request_result_success = "SUCCESS|Request Result success true"
    request_result_empty = "EMPTY RESULT|Response Empty Result"
    request_empty_error_msg = "Empty Error Message.."
    for call_node in function_call_result:
        # tool_call_output = call_node["output"] if "output" in call_node else {}
        tool_call_output = call_node
        status_code = tool_call_output["status_code"] if "status_code" in tool_call_output else ""
        result = tool_call_output["result"] if "result" in tool_call_output else ""
        # print("call_node: ", call_node)
        # print("tool_call_output: ", tool_call_output)
        # print("status_code: ", status_code)
        # print("result: ", result)
        if status_code != 200:
            result_list.append(request_failed)
            result_success_label_list.append(0)
        else:
            ## http sucess
            result_json = {}
            if isinstance(result, dict):
                result_json = result
            else:
                try:
                    result_json = json.loads(result)
                except Exception as e:
                    print (e)

            if_success = result_json["success"] if "success" in result_json else False
            data = result_json["data"] if "data" in result_json else {}
            error = result_json["error"] if "error" in result_json else ""

            empty_data = False
            if isinstance(data, list):
                empty_data = True if len(data) == 0 or (len(data) > 0 and data[0] == "") or (len(data) > 0 and len(data[0]) == 0) else False  # [{}]
            elif isinstance(data, dict):
                values = "".join([v for k,v in data.items()])
                empty_data = True if len(data) == 0 or (len(data) > 0 and values == "") else False 
            elif isinstance(data, str):
                empty_data = True if len(data) == 0 or (len(data) > 0 and data in ["[]", "\"\"", "\"[]\""])  else False 
            else:
                empty_data = False

            if if_success:
                if empty_data:
                    result_list.append(request_result_empty)
                    result_success_label_list.append(0)
                else:
                    result_list.append(request_result_success)
                    result_success_label_list.append(1)
            else:
                ## sucess false append error logs
                if error != "":
                    # check data
                    result_list.append(str(error))
                    result_success_label_list.append(0)
                else:
                    result_list.append(request_empty_error_msg)
                    result_success_label_list.append(0)
    
    # print("result_success_label_list: ", result_success_label_list)
    # print("result_list: ", result_list)
    return {
        "result_success_label_list": result_success_label_list,
        "result_list": result_list
    }
    # return result_success_label_list, result_list


def base_compare_result(predict_result: Any, label_result: Any) -> bool:
    """
        Compare Exact Value match, e.g. 3 == 3, "New York" == "New York"
    """
    return label_result == predict_result

def base_compare_result_status_dict(predict_result: dict, label_result: dict) -> bool:
    """
        label_result: 
        {
            'success': True, 'data': ['Navigated to https://www.stackoverflow.com'], 'error': None}, 
            'status_code': 200
        }
        predict_result:
        {
            'status_code': 200,
            "result": {'status_code': 200, 'result': {}}, 'step': '1', 'id': '1'}
        }
    """
    status_code = predict_result["status_code"] if "status_code" in predict_result else 500
    if status_code == 200:
        return True
    return False

def base_compare_result_search(predict_result: dict, label_result: dict) -> bool:
    """
        Search Result is NOT Empty
    """
    if len(label_result) > 0:
        return True
    return False


def estimate_pass_at_k(num_samples, num_correct, k):
    """Estimates pass@k of each problem and returns them in an array.
        Reference: Implementation from LiveCodeBench: https://github.com/LiveCodeBench/LiveCodeBench
    """

    def estimator(n: int, c: int, k: int) -> float:
        """Calculates 1 - comb(n - c, k) / comb(n, k)."""
        if n - c < k:
            return 1.0
        return 1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))

    import itertools

    if isinstance(num_samples, int):
        num_samples_it = itertools.repeat(num_samples, len(num_correct))
    else:
        assert len(num_samples) == len(num_correct)
        num_samples_it = iter(num_samples)

    return np.array(
        [estimator(int(n), int(c), k) for n, c in zip(num_samples_it, num_correct)]
    )


_global_tool_result_check_func_provider: Dict[str, Any] = {}
_global_tool_result_check_func_provider[KEY_BASE_COMPARE_FUNC] = base_compare_result


## example: add special tool result compare
_global_tool_result_check_func_provider["playwright_navigate"] = base_compare_result_status_dict
_global_tool_result_check_func_provider["bing_web_search"] = base_compare_result_search
_global_tool_result_check_func_provider["bing_news_search"] = base_compare_result_search


def run_test_pass_k():

    num_samples = [10, 10, 10]
    num_correct = [3, 3, 5]
    k = 1

    # array([0.3, 0.3, 0.5])
    pass_at_k = estimate_pass_at_k(num_samples, num_correct, k)
    final_pass_at_k = sum(pass_at_k)/len(pass_at_k)
    print (f"Final Pass @k equals {final_pass_at_k}")


    pass_at_5 = estimate_pass_at_k([10], [5], 5) # e.g.  0.99603175

    # pass@ n = 10, k = 1 

def main():

    run_test_pass_k()


if __name__ == "__main__":
    main()
