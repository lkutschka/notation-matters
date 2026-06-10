#!/usr/bin/env python3
"""Aggregate schema / tool-call / tool-result tokens across the three benchmarks
that emit per-substitution-point token tracking (StableToolBench, MCPToolBenchPP,
MCP-Universe). BFCL only tracks input/output totals per turn and is omitted.

Output: token_decomposition.json with shape
    {"<benchmark>__<model>__<variant>": {
        "schema": int, "call": int, "result": int, "total": int
    }, ...}
variant is "<fmt>" (input-only) or "<fmt>_full" (full).
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_PATH = ROOT / "token_decomposition.json"

# Map cluster-side strict-dir names -> short model keys (mirrors build_data_dict.py)
MODEL_KEY = {
    "mistral-small-24b-strict":          "mistral",
    "qwen3-32b-awq-strict":              "qwen-think",
    "qwen3-32b-awq-strict-nothink":      "qwen-nothink",
    "deepseek-r1-32b-strict":            "deepseek-r1",
    "llama4-scout-strict":               "llama-4",
}
MODEL_KEYS_BY_LEN = sorted(MODEL_KEY.keys(), key=len, reverse=True)


def find_base(name: str):
    for base in MODEL_KEYS_BY_LEN:
        if name == base or name.startswith(base + "-") or name.startswith(base + "_"):
            return base
    return None


# ─── StableToolBench ───────────────────────────────────────────────────────────
# Dir name pattern: <model-strict>_<tool_format>_tc<tool_call_format>
# input-only: <fmt>_tcjson; full: <fmt>_tc<fmt>

def collect_stb():
    out = defaultdict(lambda: {"schema": 0, "call": 0, "result": 0, "total": 0})
    root = ROOT / "StableToolBench" / "results"
    if not root.exists():
        return {}
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        name = d.name
        base = find_base(name)
        if base is None:
            continue
        suffix = name[len(base):]
        m = re.match(r"_(json|toon|tron)_tc(json|toon|tron)$", suffix)
        if not m:
            continue
        fmt, tc_fmt = m.group(1), m.group(2)
        is_full = (tc_fmt != "json") if fmt != "json" else False
        variant = fmt + ("_full" if is_full else "")
        model = MODEL_KEY[base]
        for fp in d.rglob("*.json"):
            try:
                obj = json.loads(fp.read_text())
            except Exception:
                continue
            ag = obj.get("answer_generation") or {}
            schema_t = int(ag.get("schema_tokens", 0) or 0)
            call_in  = int(ag.get("tool_call_input_tokens", 0) or 0)
            call_out = int(ag.get("tool_call_output_tokens", 0) or 0)
            result_t = int(ag.get("tool_result_tokens", 0) or 0)
            total    = int(ag.get("total_tokens", 0) or 0)
            key = f"StableToolBench__{model}__{variant}"
            agg = out[key]
            agg["schema"] += schema_t
            agg["call"]   += call_in + call_out  # both directions of the tool-call
            agg["result"] += result_t
            agg["total"]  += total
    return dict(out)


# ─── MCPToolBenchPP ─────────────────────────────────────────────────────────────
# resume.json filenames: <suite>_<fmt>_tc<tc_fmt>_<model-strict>_resume.json
# token_usage contains total_local_mcp_schema_tokens,
# total_local_tool_call_output_tokens, total_local_tool_result_tokens, plus totals.

def collect_benchpp():
    out = defaultdict(lambda: {"schema": 0, "call": 0, "result": 0, "total": 0})
    root = ROOT / "MCPToolBenchPP" / "logs"
    if not root.exists():
        return {}
    pat = re.compile(r"_(json|toon|tron)_tc(json|toon|tron)_(.+)_resume\.json$")
    for fp in root.rglob("*_resume.json"):
        m = pat.search(fp.name)
        if not m:
            continue
        fmt, tc_fmt, model_str = m.group(1), m.group(2), m.group(3)
        base = find_base(model_str)
        if base is None:
            continue
        is_full = (tc_fmt != "json") if fmt != "json" else False
        variant = fmt + ("_full" if is_full else "")
        model = MODEL_KEY[base]
        try:
            obj = json.loads(fp.read_text())
        except Exception:
            continue
        tu = (obj.get("run_info") or {}).get("token_usage") or {}
        schema_t = int(tu.get("total_local_mcp_schema_tokens", 0) or 0)
        call_t   = int(tu.get("total_local_tool_call_output_tokens", 0) or 0)
        result_t = int(tu.get("total_local_tool_result_tokens", 0) or 0)
        total    = int(tu.get("total_api_total_tokens", 0)
                       or (tu.get("total_api_prompt_tokens", 0) or 0)
                          + (tu.get("total_api_completion_tokens", 0) or 0))
        key = f"MCPToolBenchPP__{model}__{variant}"
        agg = out[key]
        agg["schema"] += schema_t
        agg["call"]   += call_t
        agg["result"] += result_t
        agg["total"]  += total
    return dict(out)


# ─── MCP-Universe ───────────────────────────────────────────────────────────────
# Per-category markdown reports under log/test_full_report_<model-strict>/<category>_<fmt>_tc<tc_fmt>
# Per-task row columns include: Schema Tok, Call Tok, Result Tok, Total Tok.

def collect_universe():
    out = defaultdict(lambda: {"schema": 0, "call": 0, "result": 0, "total": 0})
    root = ROOT / "MC-Universe" / "log"
    if not root.exists():
        return {}
    fname_pat = re.compile(r"^(.+)_(json|toon|tron)_tc(json|toon|tron)$")
    # data rows look like:
    # |**mcpuniverse/.../task.json**:| P | NP | Sc | Calls | Format | Prompt | Compl | Total | Cost | Schema | Call | Result |
    row_pat = re.compile(
        r"^\|\*\*[^*]+\*\*:\|\s*[\d\.\-]+\s*\|\s*[\d\.\-]+\s*\|\s*[\d\.]+\s*\|\s*\d+\s*\|"
        r"\s*[A-Z]+\s*\|\s*\d+\s*\|\s*\d+\s*\|\s*(\d+)\s*\|"  # group 1 = Total Tok
        r"\s*\$?[\d\.]+\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)"  # groups 2-4 = Schema, Call, Result
    )
    for model_dir in sorted(root.iterdir()):
        if not model_dir.is_dir() or not model_dir.name.startswith("test_full_report_"):
            continue
        base = find_base(model_dir.name[len("test_full_report_"):])
        if base is None:
            continue
        model = MODEL_KEY[base]
        for fp in model_dir.iterdir():
            if not fp.is_file():
                continue
            m = fname_pat.match(fp.name)
            if not m:
                continue
            category, fmt, tc_fmt = m.group(1), m.group(2), m.group(3)
            is_full = (tc_fmt != "json") if fmt != "json" else False
            variant = fmt + ("_full" if is_full else "")
            try:
                text = fp.read_text()
            except Exception:
                continue
            key = f"MCP-Universe__{model}__{variant}"
            agg = out[key]
            for row in text.splitlines():
                rm = row_pat.search(row)
                if not rm:
                    continue
                total, schema, call, result = (int(rm.group(i)) for i in (1, 2, 3, 4))
                agg["schema"] += schema
                agg["call"]   += call
                agg["result"] += result
                agg["total"]  += total
    return dict(out)


def main():
    all_data = {}
    all_data.update(collect_stb())
    all_data.update(collect_benchpp())
    all_data.update(collect_universe())
    # Round trip to plain dict for json dump
    serialisable = {k: dict(v) for k, v in all_data.items()}
    OUT_PATH.write_text(json.dumps(serialisable, indent=2, sort_keys=True))
    print(f"Wrote {len(serialisable)} cells to {OUT_PATH}")

    # Aggregate schema / call / result max savings per format vs JSON
    print()
    print("=== Aggregate savings vs JSON per substitution point ===")
    for cond, suf in [("input-only", ""), ("full", "_full")]:
        print(f"\n--- {cond} ---")
        for fmt in ("toon", "tron"):
            for part in ("schema", "call", "result"):
                tot_json = tot_fmt = 0
                # Sum across (benchmark, model)
                for k, v in serialisable.items():
                    bench, model, variant = k.split("__")
                    if variant == "json":
                        json_key = k
                        fmt_key = f"{bench}__{model}__{fmt}{suf}"
                        if fmt_key in serialisable and v[part] > 0:
                            tot_json += v[part]
                            tot_fmt  += serialisable[fmt_key][part]
                if tot_json:
                    delta = (tot_fmt - tot_json) / tot_json * 100
                    print(f"  {part:7s} {fmt.upper():5s}: aggregate {tot_json:>12,d} -> {tot_fmt:>12,d}  ({delta:+.1f}%)")


if __name__ == "__main__":
    main()
