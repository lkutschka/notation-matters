"""
The class for a generate a report
"""
# pylint: disable=broad-exception-caught
import uuid
from datetime import datetime
from typing import List, Dict
from pathlib import Path
from collections import defaultdict
from mcpuniverse.agent.base import TOOL_RESPONSE_SUMMARIZER_PROMPT
from mcpuniverse.tracer.collectors import BaseCollector
from .runner import BenchmarkResult, BenchmarkConfig, BenchmarkRunner

REPORT_FOLDER = Path('log')


class BenchmarkReport:
    """
    Class for generating a benchmark report.
    """

    def __init__(self, runner: BenchmarkRunner, trace_collector: BaseCollector, log_dir: str = "", log_name: str = ""):
        self.benchmark_configs: List[BenchmarkConfig] = runner._benchmark_configs
        self.benchmark_results: List[BenchmarkResult] = runner._benchmark_results
        self.benchmark_agent_configs: List[Dict] = runner._agent_configs
        self.trace_collector = trace_collector
        self.log_dir = log_dir
        self.log_name = log_name

        self.llm_configs = [x for x in self.benchmark_agent_configs if x['kind'] == 'llm']
        assert len(self.llm_configs) == 1, "the number of llm configs should be 1"
        self.llm_configs = self.llm_configs[0]

        self.agent_configs = [x for x in self.benchmark_agent_configs if x['kind'] == 'agent']
        assert len(self.agent_configs) == 1, "the number of agent configs should be 1"
        self.agent_configs = self.agent_configs[0]

        assert len(self.benchmark_configs) == len(
            self.benchmark_results), "benchmark_configs and benchmark_result should have the same length"
        self.log_file = ''

    def dump(self):
        """Dump the result to a report, will dump to REPORT_FOLDER"""
        final_report_str = []

        for benchmark_idx, (benchmark_config, benchmark_result) in enumerate(
                zip(self.benchmark_configs, self.benchmark_results)):
            # Generate different sections of the report
            section_config = self._generate_config_section(benchmark_config)
            section_summary = self._generate_summary_section()
            section_details = self._generate_details_section(benchmark_result, benchmark_idx, section_summary)

            # Combine all sections
            final_report_str.extend(section_config)
            final_report_str.extend(section_summary)
            final_report_str.extend(section_details)

        final_report_str = '\n'.join(final_report_str)
        self.write_to_report(final_report_str)

    def _generate_config_section(self, benchmark_config):
        """Generate the configuration section of the report."""
        section_config = []
        section_config.append("## Benchmark Config\n")
        section_config.append(f"**Benchmark description:** {benchmark_config.description}\n")
        section_config.append(f"**Agent:** {benchmark_config.agent}\n")
        section_config.append(
            f"**LLM:** {self.llm_configs['spec']['type']}: {self.llm_configs['spec']['config']['model_name']}\n")
        # Show tool format if configured
        tool_format = self.agent_configs.get('spec', {}).get('config', {}).get('tool_format', 'json')
        section_config.append(f"**Tool Format:** {tool_format.upper()}\n")
        return section_config

    def _generate_summary_section(self):
        """Generate the summary section header of the report."""
        section_summary = []
        section_summary.append("## Benchmark Summary")
        section_summary.append(
            "| Name | Passed | Not Passed | Score | LLM Calls | Format | Prompt Tok | Compl Tok | Total Tok | Cost USD | Schema Tok | Call Tok | Result Tok |\n"
            "| ---  | ------ | ---------- | ----- | --------- | ------ | ---------- | --------- | --------- | -------- | ---------- | ------- | ---------- |"
        )
        return section_summary

    def _generate_details_section(self, benchmark_result, benchmark_idx, section_summary):
        """Generate the details section of the report."""
        section_details = []
        section_details.append("## Appendix (Benchmark Details)")

        for task_name in benchmark_result.task_results.keys():
            task_details, task_passed, task_notpassed, llm_call_count, total_turns, format_metrics = \
                self._process_task(task_name, benchmark_result, benchmark_idx)
            section_details.extend(task_details)
            if llm_call_count == 0:
                llm_call_count = total_turns

            # Extract format metrics for summary
            fmt = format_metrics.get("tool_format", "json").upper()
            schema_tok = format_metrics.get("mcp_schema_tokens", 0)
            call_tok = format_metrics.get("tool_call_output_tokens", 0)
            result_tok = format_metrics.get("tool_result_tokens", 0)
            prompt_tok = format_metrics.get("prompt_tokens", 0)
            compl_tok = format_metrics.get("completion_tokens", 0)
            total_tok = format_metrics.get("total_tokens", 0)
            cost = format_metrics.get("cost_usd", 0.0)
            format_violations = format_metrics.get("format_violations", 0)

            # Add to summary (extra trailing column = format_violations count)
            section_summary.append(
                f"|**{task_name}**:| "
                f"{task_passed} | "
                f"{task_notpassed} | "
                f"{task_passed / (task_passed + task_notpassed):.2f} | "
                f"{llm_call_count} | "
                f"{fmt} | "
                f"{prompt_tok} | "
                f"{compl_tok} | "
                f"{total_tok} | "
                f"${cost:.6f} | "
                f"{schema_tok} | "
                f"{call_tok} | "
                f"{result_tok} | "
                f"{format_violations} |"
            )

        return section_details

    def _process_task(self, task_name, benchmark_result, benchmark_idx):
        """Process a single task and return its details."""
        trace_id = self.benchmark_results[benchmark_idx].task_trace_ids.get(task_name)
        stats, parent_ids, llm_call_count, total_turns = self._analyze_traces(trace_id)

        task_details = []
        task_details.append("### Task")
        task_details.append(f"- config: {task_name}")

        if parent_ids:
            task_details.append(f"- parent_id: {', '.join(parent_ids)}")

        task_details.append(f"- LLM Call Count: {llm_call_count}")
        if total_turns > 0:
            task_details.append(f"- Agent Turns: {total_turns}")

        # Add performance metrics
        self._add_performance_metrics(task_details, trace_id)

        # Add resource utilization metrics
        resource_metrics = self._add_resource_metrics(task_details, trace_id)

        # Add format metrics (local token counts)
        format_metrics = self._add_format_metrics(task_details, trace_id)
        format_metrics.update(resource_metrics)

        # Add agent response stats
        task_details.append("- Agent Response:")
        for key, value in stats.items():
            task_details.append(f"  - {key}: {value}\n")

        # Add trace structure
        self._add_trace_structure(task_details, trace_id)

        # Process evaluation results
        eval_results = benchmark_result.task_results[task_name]["evaluation_results"]
        task_passed, task_notpassed = self._process_evaluation_results(task_details, eval_results)

        return task_details, task_passed, task_notpassed, llm_call_count, total_turns, format_metrics

    def _analyze_traces(self, trace_id):
        """Analyze traces and return stats, parent IDs, and LLM call count."""
        stats = defaultdict(int)
        parent_ids = set()
        llm_call_count = 0
        total_turns = 0

        for task_trace in self.trace_collector.get(trace_id):
            if not task_trace.records:
                continue
            iter_type = task_trace.records[0].data['type']
            iter_name = iter_type

            if iter_type == 'llm':
                if task_trace.records[0].data['messages'][0]['role'] == 'raw':
                    iter_name = "llm_prompt"
                else:
                    summary_prompt = TOOL_RESPONSE_SUMMARIZER_PROMPT[:20]
                    is_summarized = task_trace.records[0].data['messages'][0]['content'].startswith(summary_prompt)
                    print(iter_type, is_summarized)
                    iter_name = f"llm_{'summary' if is_summarized else 'thought'}"
                llm_call_count += 1
            elif iter_type == 'openai_agent_sdk':
                # Extract turns information from OpenAI Agent SDK traces
                turns = task_trace.records[0].data.get('turns', 1)
                total_turns += turns
                print(f"OpenAI Agent SDK: {turns} turns")
                continue
            else:
                continue

            stats[iter_name] += 1

            if task_trace.parent_id:
                parent_ids.add(task_trace.parent_id)

        return stats, parent_ids, llm_call_count, total_turns

    def _add_performance_metrics(self, task_details, trace_id):
        """Add performance and resource usage statistics."""
        total_execution_time = sum(task_trace.running_time for task_trace in self.trace_collector.get(trace_id))
        total_records = sum(len(task_trace.records) for task_trace in self.trace_collector.get(trace_id))
        trace_list = list(self.trace_collector.get(trace_id))
        avg_response_time = total_execution_time / max(len(trace_list), 1)

        task_details.append(f"- Total Execution Time: {total_execution_time:.2f}s")
        task_details.append(f"- Average Response Time: {avg_response_time:.2f}s")
        task_details.append(f"- Total Records: {total_records}")

    def _add_resource_metrics(self, task_details, trace_id):
        """Add resource utilization metrics. Returns dict with totals."""
        result = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }
        llm_traces = [t for t in self.trace_collector.get(trace_id)
                      if t.records and t.records[0].data.get('type') == 'llm']

        if not llm_traces:
            return result

        # Calculate total prompt tokens
        result["prompt_tokens"] = sum(
            (t.records[0].data.get('usage') or {}).get('prompt_tokens', 0) or 0
            for t in llm_traces
        )
        # Calculate total completion tokens
        result["completion_tokens"] = sum(
            (t.records[0].data.get('usage') or {}).get('completion_tokens', 0) or 0
            for t in llm_traces
        )
        result["total_tokens"] = result["prompt_tokens"] + result["completion_tokens"]
        # Calculate total cost (OpenRouter provides cost_usd)
        result["cost_usd"] = sum(
            (t.records[0].data.get('usage') or {}).get('cost_usd', 0.0) or 0.0
            for t in llm_traces
        )

        if result["prompt_tokens"]:
            task_details.append(f"- Total Prompt Tokens: {result['prompt_tokens']}")
        if result["completion_tokens"]:
            task_details.append(f"- Total Completion Tokens: {result['completion_tokens']}")
        if result["total_tokens"]:
            task_details.append(f"- Total Tokens Used: {result['total_tokens']}")
        if result["cost_usd"]:
            task_details.append(f"- Total Cost (USD): ${result['cost_usd']:.6f}")

        return result

    def _add_format_metrics(self, task_details, trace_id):
        """Add format-specific token metrics from agent_format_metrics traces."""
        format_traces = [
            t for t in self.trace_collector.get(trace_id)
            if t.records and t.records[0].data.get('type') == 'agent_format_metrics'
        ]

        result = {
            "tool_format": "json",
            "mcp_schema_tokens": 0,
            "tool_call_output_tokens": 0,
            "tool_result_tokens": 0,
            "format_violations": 0,
        }

        if not format_traces:
            return result

        # Take the last format metrics trace (recorded at end of _execute)
        data = format_traces[-1].records[0].data
        tool_format = data.get('tool_format', 'json')
        local_counts = data.get('local_token_counts', {})

        result["tool_format"] = tool_format
        result["mcp_schema_tokens"] = local_counts.get('mcp_schema_tokens', 0)
        result["tool_call_output_tokens"] = local_counts.get('tool_call_output_tokens', 0)
        result["tool_result_tokens"] = local_counts.get('tool_result_tokens', 0)
        result["format_violations"] = data.get('format_violations', 0)
        format_overhead = result["mcp_schema_tokens"] + result["tool_call_output_tokens"] + result["tool_result_tokens"]

        task_details.append(f"- Tool Format: {tool_format.upper()}")
        task_details.append(f"- MCP Schema Tokens (local): {result['mcp_schema_tokens']}")
        task_details.append(f"- Tool Call Output Tokens (local): {result['tool_call_output_tokens']}")
        task_details.append(f"- Tool Result Tokens (local): {result['tool_result_tokens']}")
        task_details.append(f"- Format Overhead Total: {format_overhead}")
        task_details.append(f"- Format Violations: {result['format_violations']}")

        return result

    def _add_trace_structure(self, task_details, trace_id):
        """Add detailed trace structure information."""
        task_details.append("- Trace Structure:")
        trace_structure = defaultdict(list)

        for task_trace in self.trace_collector.get(trace_id):
            if task_trace.parent_id:
                trace_info = self._extract_trace_info(task_trace)
                trace_structure[task_trace.parent_id].append(trace_info)

        self._format_trace_structure(task_details, trace_structure)

    def _extract_trace_info(self, task_trace):
        """Extract comprehensive trace information."""
        first_record = task_trace.records[0] if task_trace.records else None
        usage_data = (first_record.data.get('usage') or {}) if first_record else {}

        return {
            'id': task_trace.id,
            'span_index': task_trace.span_index,
            'running_time': task_trace.running_time,
            'timestamp': task_trace.timestamp,
            'record_count': len(task_trace.records),
            'iter_type': (first_record.data.get('type', 'unknown')
                          if first_record else 'unknown'),
            'iter_tool_name': (first_record.data.get('tool_name', '')
                               if first_record else ''),
            'iter_prompt_tokens': usage_data.get('prompt_tokens', ''),
            'iter_completion_tokens': usage_data.get('completion_tokens', ''),
            'iter_total_tokens': usage_data.get('total_tokens', ''),
            'iter_error': (first_record.data.get('error', '')
                           if first_record else ''),
        }

    def _format_trace_structure(self, task_details, trace_structure):
        """Format and display hierarchical trace structure."""
        for parent_id, children in trace_structure.items():
            task_details.append(f"  - Parent Trace: {parent_id}")
            for child in children:
                # Basic trace information
                trace_line = (f"    - Child: {child['id']} (span: {child['span_index']}, "
                              f"time: {child['running_time']:.2f}s, type: {child['iter_type']})")
                task_details.append(trace_line)

                # Detailed trace metadata
                self._add_trace_metadata(task_details, child)

    def _add_trace_metadata(self, task_details, child):
        """Add detailed trace metadata."""
        if child['iter_tool_name']:
            task_details.append(f"      - Tool: {child['iter_tool_name']}")
        if child['iter_prompt_tokens']:
            task_details.append(f"      - Prompt Tokens: {child['iter_prompt_tokens']}")
        if child['iter_completion_tokens']:
            task_details.append(f"      - Completion Tokens: {child['iter_completion_tokens']}")
        if child['iter_total_tokens']:
            task_details.append(f"      - Total Tokens: {child['iter_total_tokens']}")
        if child['iter_error']:
            task_details.append(f"      - Error: {child['iter_error']}")

        # Record count and timestamp information
        task_details.append(f"      - Records: {child['record_count']}")
        timestamp_str = datetime.fromtimestamp(child['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        task_details.append(f"      - Timestamp: {timestamp_str}")

    def _process_evaluation_results(self, task_details, eval_results):
        """Process evaluation results and return pass/fail counts."""
        task_details.append("- Evaluation Results: \n")

        task_passed = 0
        task_notpassed = 0

        for eval_idx, eval_result in enumerate(eval_results, start=1):
            task_details.append(f"  - Eval id: {eval_idx}")
            task_details.append(f"    - Evaluation Description: {eval_result.config.desc}\n")

            if eval_result.passed:
                eval_passed = '<span color="green">True<span>'
                task_passed += 1
            else:
                eval_passed = '<span color="red">False<span>'
                task_notpassed += 1
                if eval_result.reason:
                    task_details.append(f"    - Reason: {eval_result.reason}\n")
                if eval_result.error:
                    task_details.append(f"    - Error: {eval_result.error}\n")

            task_details.append(f"    - Passed? {eval_passed}\n")

        return task_passed, task_notpassed

    def write_to_report(self, report_str):
        """Write a report in MD format."""
        REPORT_FOLDER.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4()
        if self.log_dir and self.log_name:
            (REPORT_FOLDER / f"{self.log_dir}").mkdir(parents=True, exist_ok=True)
            report_name = REPORT_FOLDER / f"{self.log_dir}" / f"{self.log_name}"
        else:
            report_name = REPORT_FOLDER / f"report_{timestamp}_{unique_id}.md"
        try:
            with open(report_name, "w", encoding="utf-8") as f:
                f.write(report_str)
        except Exception as e:
            print(f"Write report error: {e}")
