# notation-matters

Software accompanying the paper. Modifications to four published agent benchmarks that let you swap the serialization format used for tool schemas, tool calls, and tool results between **JSON**, **TOON**, and **TRON**, via a single shared library.

## What this repo contains

```
shared_format/        Our library: format converters, strict deserializer,
                      prompt building blocks, token counter
toon-python/          TOON format library (vendored)
tron-python/          TRON format library (vendored)

gorilla/              Berkeley Function Calling Leaderboard (BFCL v4)
                      + integration with shared_format
MCP-Universe/         MCP-Universe multi-turn ReAct agent benchmark
                      + integration with shared_format
MCPToolBenchPP/       MCPToolBenchPP single-turn MCP benchmark
                      + integration with shared_format
StableToolBench/      StableToolBench multi-turn function-calling benchmark
                      + integration with shared_format
```

## How the integration works

Each benchmark imports a small surface from `shared_format`:

| Symbol | Purpose |
|---|---|
| `ToolFormat` | `JSON` / `TOON` / `TRON` enum |
| `serialize(obj, fmt)` | Encode a Python object as the given format |
| `deserialize_strict(text, fmt)` | Decode a string in the given format, raising `FormatViolation` on any deviation |
| `serialize_tools(tools, fmt)` | Render a tool catalog in the format-specific shape that fits into a system prompt |
| `get_format_explanation(fmt)` / `get_format_intro(fmt)` / `get_format_reminder(fmt)` | Prompt snippets that teach the model how to emit the format |
| `count_tokens(text)` | tiktoken-based token counter for the analysis tables |

The benchmark code drops these calls into its existing prompt-assembly and response-parsing paths. A `tool_format` and `tool_call_format` option is added to each benchmark's CLI so input format and output format can be controlled independently.

## How to use

Each benchmark keeps its own README and install story. To enable the JSON/TOON/TRON switch:

1. `pip install -e shared_format/ toon-python/ tron-python/`
2. Then `pip install -e <benchmark>/` per its own README.
3. Pass `--tool_format {json|toon|tron}` and (where applicable) `--tool_call_format {json|toon|tron}` when invoking the benchmark.

For BFCL set the env var `BFCL_PROMPT_FORMAT_OVERRIDE=ret_fmt=toon&tool_call_tag=False&func_doc_fmt=toon&prompt_fmt=plaintext&style=classic` to override the prompt format per run.

## Upstream benchmarks and credit

The four benchmarks and the TOON library are vendored here as modified snapshots so the experiments are self-contained and reproducible. All credit for the original benchmarks goes to their authors. Please cite the originals alongside this software:

| Component | Upstream | License |
|---|---|---|
| BFCL v4 (Gorilla) | https://github.com/ShishirPatil/gorilla | Apache-2.0 |
| MCP-Universe | https://github.com/SalesforceAIResearch/MCP-Universe | Apache-2.0 |
| MCPToolBench++ | https://github.com/mcp-tool-bench/MCPToolBenchPP | see repo |
| StableToolBench (builds on ToolBench) | https://github.com/OpenBMB/ToolBench | Apache-2.0 |
| toon-python | https://github.com/toon-format/toon-python | see repo |
| tron-python | TRON serialization library (part of this work) | see `tron-python/LICENSE` |

## License

The root of this repository and `shared_format/` are released under the **MIT License** (see `LICENSE`). This MIT license covers only our own contributions (`shared_format/` and the integration code added to each benchmark). Every vendored benchmark and library **retains its own upstream license**, preserved in its subdirectory (for example `gorilla/LICENSE`, `MCP-Universe/LICENSE.txt`, `StableToolBench/LICENSE`, `toon-python/LICENSE`, `tron-python/LICENSE`). Where a vendored component's license differs from MIT, that component's own license governs it.
