#!/usr/bin/env python3
"""Run a single benchmark config and print results."""
import asyncio
import sys
from mcpuniverse.tracer.collectors import FileCollector
from mcpuniverse.benchmark.runner import BenchmarkRunner
from mcpuniverse.benchmark.report import BenchmarkReport
from mcpuniverse.callbacks.handlers.vprint import get_vprint_callbacks


async def main(config_path):
    name = config_path.split("/")[-1].replace(".yaml", "")
    trace_collector = FileCollector(log_file=f"log/test_single/{name}.log")
    benchmark = BenchmarkRunner(config_path)
    results = await benchmark.run(
        trace_collector=trace_collector,
        callbacks=get_vprint_callbacks(),
    )

    report = BenchmarkReport(benchmark, trace_collector=trace_collector,
                             log_dir="test_single_report", log_name=name)
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
        print("Usage: python run_single_test.py <config.yaml>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
