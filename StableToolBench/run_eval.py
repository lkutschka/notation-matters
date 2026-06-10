"""Convert StableToolBench results and run pass rate evaluation using local LLM judge."""
import json, os, sys, re, random
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

sys.path.insert(0, 'toolbench/tooleval')
sys.path.insert(0, 'toolbench/inference')

from evaluators import load_registered_automatic_evaluator
from evaluators.registered_cls.rtl import AnswerStatus

RESULTS_BASE = "results"
EVAL_OUT = "eval_results"
SOLVABLE_DIR = "solvable_queries/test_instruction"
GROUPS = ["G1_instruction", "G2_instruction", "G3_instruction"]
FORMATS = [
    ("json_tcjson", "JSON"),
    ("toon_tctoon", "TOON"),
    ("tron_tctron", "TRON"),
]
EVALUATE_TIMES = 3
EVALUATOR_NAME = os.environ.get("EVALUATOR", "tooleval_gpt4o_mini")


def convert_result(data):
    """Convert a single result file to the eval format."""
    ag = data.get("answer_generation", {})
    query = ag.get("query", "")
    functions = ag.get("function", [])
    final_answer = ag.get("final_answer", "")

    # Build answer steps from trys chain
    steps = []
    trys = data.get("trys", [])
    if trys:
        chain = trys[0].get("chain", [])
        for i, node in enumerate(chain):
            nt = node.get("node_type", "")
            desc = node.get("description", "")
            if nt == "Thought":
                steps.append({"role": "assistant", "message": desc})
            elif nt == "Action":
                # Next node should be Action Input with observation
                obs = ""
                if i + 1 < len(chain):
                    obs = chain[i + 1].get("observation", "")
                steps.append({"role": "tool", "message": {
                    "name": desc,
                    "arguments": "",
                    "response": obs
                }})

    # Build linked list format expected by eval
    answer_details = []
    for step in steps:
        answer_details.append({
            "role": step["role"],
            "message": step["message"],
            "next": []
        })
    # Link them
    for i in range(len(answer_details) - 1):
        answer_details[i]["next"] = [answer_details[i + 1]]

    return {
        "query": query,
        "available_tools": [{"function": f, "type": "function"} if "name" not in f else f for f in functions] if functions else [],
        "answer": {
            "method": "CoT@1",
            "total_steps": len(steps),
            "final_answer": final_answer,
            "answer_details": [answer_details[0]] if answer_details else [{"role": "assistant", "message": "No answer", "next": []}]
        }
    }


def convert_all():
    """Convert all result files."""
    for tag, label in FORMATS:
        src = f"{RESULTS_BASE}/local_{tag}"
        dst = f"eval_converted/local_{tag}"
        os.makedirs(dst, exist_ok=True)

        for group in GROUPS:
            group_dir = os.path.join(src, group)
            if not os.path.exists(group_dir):
                continue
            converted = {}
            errors = 0
            for f in os.listdir(group_dir):
                if not f.endswith(".json"):
                    continue
                query_id = f.replace("_CoT@1.json", "")
                try:
                    data = json.load(open(os.path.join(group_dir, f)))
                    result = convert_result(data)
                    converted[query_id] = result
                except Exception as e:
                    errors += 1

            out_file = os.path.join(dst, f"{group}.json")
            json.dump(converted, open(out_file, "w"), ensure_ascii=False, indent=2)
            print(f"  {label} {group}: {len(converted)} converted, {errors} errors")


def run_eval():
    """Run pass rate evaluation."""
    evaluators = [load_registered_automatic_evaluator(
        evaluator_name=EVALUATOR_NAME,
        evaluators_cfg_path=os.path.join("toolbench/tooleval", "evaluators")
    )]

    for tag, label in FORMATS:
        print(f"\n=== Evaluating {label} ({tag}) ===")
        converted_dir = f"eval_converted/local_{tag}"
        save_dir = f"{EVAL_OUT}/local_{tag}"
        os.makedirs(save_dir, exist_ok=True)

        for group in GROUPS:
            converted_file = os.path.join(converted_dir, f"{group}.json")
            if not os.path.exists(converted_file):
                print(f"  {group}: no converted file")
                continue

            examples = json.load(open(converted_file))
            save_file = os.path.join(save_dir, f"{group}_results.json")

            # Load existing results if any
            if os.path.exists(save_file):
                results = json.load(open(save_file))
            else:
                results = {}

            solved = 0
            unsolved = 0
            unsure = 0
            total = 0

            for query_id, example in tqdm(examples.items(), desc=f"{label} {group}"):
                if query_id in results and len(results[query_id].get("is_solved", {})) >= EVALUATE_TIMES:
                    # Already evaluated
                    for v in results[query_id]["is_solved"].values():
                        if "Solved" in str(v):
                            solved += 1
                        elif "Unsolved" in str(v):
                            unsolved += 1
                        else:
                            unsure += 1
                    total += EVALUATE_TIMES
                    continue

                # Get answer steps for display
                answer_details = example["answer"]["answer_details"][0]
                answer_steps = []
                final_step = ""
                while "next" in answer_details:
                    msg = answer_details["message"]
                    role = answer_details["role"]
                    if msg and role == "tool":
                        answer_steps.append(str(msg))
                        final_step = str(msg)
                    if not answer_details["next"]:
                        break
                    answer_details = answer_details["next"][0]

                if query_id not in results:
                    results[query_id] = {
                        "query": example["query"],
                        "is_solved": {}
                    }

                for eval_round in range(EVALUATE_TIMES):
                    if str(eval_round) in results[query_id].get("is_solved", {}):
                        continue

                    evaluator = random.choice(evaluators)

                    # Check if Finish was called
                    if "'name': 'Finish'" not in str(example["answer"].get("final_answer", "")) and \
                       "Finish" not in str(example["answer"].get("answer_details", "")):
                        status = AnswerStatus.Unsolved
                    else:
                        try:
                            is_solved, reason = evaluator.check_is_solved(
                                {
                                    "query": example["query"],
                                    "available_tools": example["available_tools"],
                                },
                                example["answer"],
                            )
                            status = is_solved
                        except Exception as e:
                            print(f"    Eval error {query_id}: {e}")
                            status = AnswerStatus.Unsure

                    results[query_id]["is_solved"][str(eval_round)] = str(status)

                    if status == AnswerStatus.Solved:
                        solved += 1
                    elif status == AnswerStatus.Unsolved:
                        unsolved += 1
                    else:
                        unsure += 1
                    total += 1

                # Save after each task
                json.dump(results, open(save_file, "w"), ensure_ascii=False, indent=2)

            # Calculate pass rate (majority vote across EVALUATE_TIMES rounds)
            pass_count = 0
            for qid, r in results.items():
                votes = list(r.get("is_solved", {}).values())
                solved_votes = sum(1 for v in votes if "Solved" in str(v))
                if solved_votes > len(votes) / 2:
                    pass_count += 1

            total_tasks = len(results)
            pass_rate = pass_count / total_tasks * 100 if total_tasks else 0
            print(f"  {group}: {pass_count}/{total_tasks} passed ({pass_rate:.1f}%)")
            print(f"    Raw votes: {solved} solved, {unsolved} unsolved, {unsure} unsure")


if __name__ == "__main__":
    print("=== Step 1: Converting results ===")
    convert_all()
    print("\n=== Step 2: Running evaluation ===")
    run_eval()
    print("\n=== DONE ===")
