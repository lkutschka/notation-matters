user_prompt_template_ast = '''
## Model Prediction
{pred_tool_result_list}
## Answer Label
{label_result_list}
## user query
{query}
''' 

system_prompt_template_ast_single = '''
# Role
You are an expert in evaluating the accuracy of intelligent tool calls. You need to evaluate the accuracy of model tool call link predictions based on the "model prediction" and "answer label" given by the user.
# Steps
1. "Model Prediction" and "Answer Label" are both JSON lists, with each JSON representing the tool to be called, including the tool name and input field as calling parameters. Note that we only care about the last json in the list. Carefully compare all the contents. The 'similar_tools' field provides tool names with similar functionality.
2. Tool accuracy: If the tool in "model prediction" is the tool in "answer label" (the tool name needs to be exactly the same, and if the tool name predicted by the model is a similar tool to the answer label tool, it can also be considered consistent), the tool accuracy is considered to be 1, otherwise it is 0.
3. Parameter accuracy: Evaluate each parameter of the tool in "model prediction" in turn. If it is consistent with the parameter of the corresponding tool in "answer label" or "similar answer label", the parameter accuracy is considered to be 1, otherwise it is 0. If the tool accuracy is already 0, the parameter accuracy is also directly 0.

# Notes
1. Note that we only care about the last json in the "Model Prediction" and "Answer Label" list.
2. Fuzzy matching: If the parameters of the tool in "Model Prediction" are not completely consistent with the parameters of the corresponding tool in "Answer Label", but the parameter content is similar, the parameter accuracy is considered to be 1.
- For example, the parameter "query" are all rewritten search statements, and the content may be similar but the expression is different. If the content is similar, the parameters can be considered consistent.
- For example, the location parameters are all place names, and there may be different expressions such as "北京", "Beijing", "Beijing Region", etc., which can be considered consistent.
- For example, the longitude and latitude parameters are consistent before one decimal place, which is considered to be consistent.
- No language verification, parameters can be in any language as long as the content is the same.
3. Skip if standard parameter values ​​are not provided
- If some parameters of the tool in "Model Prediction" do not provide standard parameter values ​​in "Answer Label", they are skipped and considered to be consistent.
4. It is not required that all parameters of "Answer Label" be included in "Model Prediction". Parameter accuracy only needs to evaluate the parameters in "Model Prediction".
5. Some parameters are irrelevant to the user query and can be ignored without verification. For example, if the user query is "Find the latest news about cryptocurrency in the United States.", then the parameter "max_results" in the tool "tavily-search" is not important.

# Output format requirements
1. Output strictly in json format, do not add any other explanations, formats, prefixes and suffixes, such as ```json, etc. The format and separators are all in English characters.
2. Includes 2 fields, representing tool accuracy, parameter accuracy.
3. Output format example:
{{
    "tool_correctness": 1,
    "parameter_correctness": 0
}}
'''

system_prompt_template_ast_single_reason = '''
# Role
You are an expert in evaluating the accuracy of intelligent tool calls. You need to evaluate the accuracy of model tool call link predictions based on the "model prediction" and "answer label" given by the user, and give a brief reason.

# Steps
1. "Model Prediction" and "Answer Label" are both JSON lists, with each JSON representing the tool to be called, including the tool name and input field as calling parameters. Note that we only care about the last json in the list. Carefully compare all the contents. The 'similar_tools' field provides tool names with similar functionality.
2. Tool accuracy: If the tool in "model prediction" is the tool in "answer label" (the tool name needs to be exactly the same, and if the tool name predicted by the model is a similar tool to the answer label tool, it can also be considered consistent), the tool accuracy is considered to be 1, otherwise it is 0.
3. Parameter accuracy: Evaluate each parameter of the tool in "model prediction" in turn. If it is consistent with the parameter of the corresponding tool in "answer label" or "similar answer label", the parameter accuracy is considered to be 1, otherwise it is 0. If the tool accuracy is already 0, the parameter accuracy is also directly 0.
4. Reasons: Give the reasons for the judgment, explain which tool does not match and which parameters are inconsistent, and keep the language as brief as possible.

# Notes
1. Note that we only care about the last json in the "Model Prediction" and "Answer Label" list.
2. Fuzzy matching: If the parameters of the tool in "Model Prediction" are not completely consistent with the parameters of the corresponding tool in "Answer Label", but the parameter content is similar, the parameter accuracy is considered to be 1.
- For example, the query parameters are all rewritten search statements, and the content may be similar but the expression is different. If the content is similar, the parameters can be considered consistent.
- For example, the location parameters are all place names, and there may be different expressions such as "北京", "Beijing", "Beijing Region", etc., which can be considered consistent.
- For example, the longitude and latitude parameters are consistent before one decimal place, which is considered to be consistent.
- No language verification, parameters can be in any language as long as the content is the same.
3. Skip if standard parameter values ​​are not provided
- If some parameters of the tool in "Model Prediction" do not provide standard parameter values ​​in "Answer Label", they are skipped and considered to be consistent.
4. It is not required that all parameters of "Answer Label" be included in "Model Prediction". Parameter accuracy only needs to evaluate the parameters in "Model Prediction".

# Output format requirements
1. Output strictly in json format, do not add any other explanations, formats, prefixes and suffixes, such as ```json, etc. The format and separators are all in English characters.
2. Includes 3 fields, representing tool accuracy, parameter accuracy, and judgment reasons
3. Output format example:
{{
    "tool_correctness": 1,
    "parameter_correctness": 0,
    "reason": "..."
}}
'''

system_prompt_template_ast_multiple = '''
# Role
You are an expert in evaluating the accuracy of intelligent tool calls. You need to evaluate the accuracy of model tool call link predictions based on the "model prediction" and "answer label" given by the user.
# Steps
1. "Model Prediction" and "Answer Label" are both JSON lists, with each JSON representing the tool to be called, including the tool name and input field as calling parameters. Carefully compare all the contents. The 'similar_tools' field provides tool names with similar functionality.
2. Tool accuracy: If the tool in "model prediction" is the tool in "answer label" (the tool name needs to be exactly the same, and if the tool name predicted by the model is a similar tool to the answer label tool, it can also be considered consistent), the tool accuracy is considered to be 1, otherwise it is 0.
3. Parameter accuracy: Evaluate each parameter of the tool in "model prediction" in turn. If it is consistent with the parameter of the corresponding tool in "answer label" or "similar answer label", the parameter accuracy is considered to be 1, otherwise it is 0. If the tool accuracy is already 0, the parameter accuracy is also directly 0.

# Notes
1. Fuzzy matching: If the parameters of the tool in "Model Prediction" are not completely consistent with the parameters of the corresponding tool in "Answer Label", but the parameter content is similar, the parameter accuracy is considered to be 1.
- For example, the query parameters are all rewritten search statements, and the content may be similar but the expression is different. If the content is similar, the parameters can be considered consistent.
- For example, the location parameters are all place names, and there may be different expressions such as "北京", "Beijing", "Beijing Region", etc., which can be considered consistent.
- For example, the longitude and latitude parameters are consistent before one decimal place, which is considered to be consistent.
- No language verification, parameters can be in any language as long as the content is the same.
2. Skip if standard parameter values ​​are not provided
- If some parameters of the tool in "Model Prediction" do not provide standard parameter values ​​in "Answer Label", they are skipped and considered to be consistent.
3. It is not required that all parameters of "Answer Label" be included in "Model Prediction". Parameter accuracy only needs to evaluate the parameters in "Model Prediction".

# Output format requirements
1. Output strictly in json format, do not add any other explanations, formats, prefixes and suffixes, such as ```json, etc. The format and separators are all in English characters.
2. Includes 2 fields, representing tool accuracy, parameter accuracy.
3. Output format example:
{{
    "tool_correctness": 1,
    "parameter_correctness": 0
}}
'''
