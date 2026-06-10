#### Run

###  start server Enable MCP Tool Client
cd ./mcp/mcp-marketplace/app/mcp_tool_use
uvicorn src.app:app --port 5000

### Test Run Demo
python3 run.py --stage tool_call --input_file ./data/browser/browser_single_demo.json --category browser --model qwen3-max --pass_k 1,3 --evaluation_trial_per_task 5

## OpenAI 
python3 run.py --stage tool_call --input_file ./data/browser/browser_0713_single_500.json --category browser --model gpt-4o --pass_k 1,3
python3 run.py --stage tool_call --input_file ./data/browser/browser_0713_single_500.json --category browser --model gpt-4.1 --pass_k 1,3
python3 run.py --stage tool_call --input_file ./data/browser/browser_0713_single_500.json --category browser --model o3 --pass_k 1,3
python3 run.py --stage tool_call --input_file ./data/browser/browser_0713_single_500.json --category browser --model o3-pro --pass_k 1,3
python3 run.py --stage tool_call --input_file ./data/browser/browser_0713_single_500.json --category browser --model o4-mini --pass_k 1,3

### Claude API
python3 run.py --stage tool_call --input_file ./data/browser/browser_0713_single_500.json --category browser --model claude-opus-4-20250514 --pass_k 1,3
python3 run.py --stage tool_call --input_file ./data/browser/browser_0713_single_500.json --category browser --model claude-sonnet-4-20250514 --pass_k 1,3
python3 run.py --stage tool_call --input_file ./data/browser/browser_0713_single_500.json --category browser --model claude-3-7-sonnet-20250219 --pass_k 1,3

### Qwen API
python3 run.py --stage tool_call --input_file ./data/browser/browser_0713_single_500.json --category browser --model qwen3-max --pass_k 1,3
python3 run.py --stage tool_call --input_file ./data/browser/browser_0713_single_500.json --category browser --model qwen3-plus --pass_k 1,3
