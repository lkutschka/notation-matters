#!/usr/bin/env python3
"""Run a full benchmark config and print results."""
import asyncio
import os
import sys
from mcpuniverse.tracer.collectors import FileCollector
from mcpuniverse.benchmark.runner import BenchmarkRunner
from mcpuniverse.benchmark.report import BenchmarkReport
from mcpuniverse.callbacks.handlers.vprint import get_vprint_callbacks


async def main(config_path, resume=False):
    name = config_path.split("/")[-1].replace(".yaml", "")
    # Per-model report/trace dirs so Mistral and Qwen runs don't overwrite
    # each other (the report filename has no model component, only the
    # variant). MODEL_TAG is set by the slurm export.
    model_tag = os.environ.get("MODEL_TAG", "")
    trace_dir = f"log/test_full_{model_tag}" if model_tag else "log/test_full"
    report_dir = f"test_full_report_{model_tag}" if model_tag else "test_full_report"
    trace_collector = FileCollector(log_file=f"{trace_dir}/{name}.log")
    benchmark = BenchmarkRunner(config_path)
    results = await benchmark.run(
        trace_collector=trace_collector,
        callbacks=get_vprint_callbacks(),
        overwrite=not resume,
    )

    report = BenchmarkReport(benchmark, trace_collector=trace_collector,
                             log_dir=report_dir, log_name=name)
    report.dump()

    print("=" * 66)
    print(f"Evaluation Result: {name}")
    print("-" * 66)
    for task_name in results[0].task_results.keys():
        print(task_name)
        print("-" * 66)
        eval_results = results[0].task_results[task_name]["evaluation_results"]
        for eval_result in eval_results:
            print("func:", eval_result.config.func)
            print("op:", eval_result.config.op)
            print("value:", eval_result.config.value)
            print(
                "Passed?:",
                "\033[32mTrue\033[0m" if eval_result.passed else "\033[31mFalse\033[0m",
            )
            print("-" * 66)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_full_test.py <config.yaml> [--resume]")
        sys.exit(1)
    resume = "--resume" in sys.argv
    config = [a for a in sys.argv[1:] if not a.startswith("--")][0]
    asyncio.run(main(config, resume=resume))
