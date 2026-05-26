# Research Agent Harness

A parallel-execution agent harness for an LLM-driven D&D 5e SRD research assistant, built on the [datapizza-ai](https://pypi.org/project/datapizza-ai/) framework. The agent searches the SRD with regex/fuzzy queries, delegates independent research branches to subagents that run concurrently, and synthesizes a final cited answer.

This started from the workshop skeleton by [raul-singh/research-agent-workshop](https://github.com/raul-singh/research-agent-workshop) — I implemented the harness and tool layer (the 10 workshop TODOs) and then went further with hardening, prompt engineering, and bug fixes.

## What I built

### Agentic loop (`workshop/harness.py`)
The core loop: `client.invoke` → parse response blocks → dispatch every `FunctionCallBlock` to a `ThreadPoolExecutor` in parallel → feed results back into memory → repeat until the model emits no more tool calls.

Hardened beyond a baseline implementation:

- **Tool exceptions never crash the loop.** `_execute_tool_call` always returns a valid `FunctionCallResultBlock` — exceptions become `<tool error: ...>` payloads the model can see and recover from. Memory stays consistent (no orphaned `tool_call_id`s).
- **Per-tool timeouts.** Every future has a configurable `tool_timeout`; on expiry the future is cancelled and a timeout error block is emitted. No more indefinite hangs from a stuck network call.
- **Executor leak prevention.** `weakref.finalize` shuts down each `Agent`'s `ThreadPoolExecutor` on garbage collection, so subagents spawned inside `delegate_research` don't leak worker threads across the process lifetime.

### Tools (`workshop/agent.py`)

- **`search`** — regex + fuzzy search over the SRD markdown corpus. Returns numbered match blocks with `Source / Match / Title Path / Context`. The `@tool` docstring exposes querying strategy (exact-first, heading-retry, fuzzy is not semantic) to the model as part of the tool's contract.
- **`delegate_research`** — spawns N subagents in parallel via a per-call `ThreadPoolExecutor`. Each subagent runs in isolation: fresh memory, only the `search` tool, no recursive delegation. Aggregated output preserves submission order so the main model can reference findings by index. Failed subagents are emitted as `[S{i}] FAILED — Error: ...` so they're visually distinct from real answers.

### Prompt engineering
Tightened the delegation trigger in `workshop/prompt.py` with crisp heuristics ("3+ named entities → delegate"), concrete `delegate_research(tasks=[...])` examples, and explicit anti-patterns (regex alternation hacks, sequential search loops). Before: model chose direct sequential `search` on most multi-entity queries. After: model picks `delegate_research` on the first tool call, every time.

### Bugs caught during real testing
- **Windows `cp1252` codec crash.** Model output containing `→`, em-dashes, or curly quotes silently killed one subagent per call on Windows because the default console encoding can't represent them. Fixed by forcing `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at process start.
- **`cwd`-relative paths.** `load_structure()` and the search folder used paths relative to the current working directory, so `python main.py` worked from the project folder and crashed from anywhere else. Anchored all paths to `__file__` via `PROJECT_ROOT = Path(__file__).resolve().parent.parent`.

### Optimizations
- Subagent `tool_executor` reduced from 8 → 4 workers (subagents only have one tool and rarely run it in parallel) — halves the thread footprint per delegated call (5 × 8 = 40 → 5 × 4 = 20).
- `max_parallel` in `delegate_research` is type-coerced (handles the model passing `"4"` as a string) and capped at 8 to prevent thread/socket exhaustion.
- `--compact` CLI flag exposes one-line-per-event log output for cleaner runs.

## Sample run

```
$ uv run main.py -q "Compare damage and range of Fireball, Lightning Bolt, and Cone of Cold." --compact

[Main] [tool] delegate_research tasks=[3 item(s)] max_parallel=3
[delegate] dispatching 3 task(s) with up to 3 parallel subagent(s)
[S1] [task] S1 spawned   task: Find the SRD entry for Fireball ...
[S2] [task] S2 spawned   task: Find the SRD entry for Lightning Bolt ...
[S3] [task] S3 spawned   task: Find the SRD entry for Cone of Cold ...
[S1] [tool] search       query="# Fireball" document="DND5eSRD_121-137.md" ...
[S1] done in 5.0s
[S3] done in 5.2s
[S2] done in 9.5s
[Main] [answer]

Answer:
| Spell           | Damage              | Range  | Area                        |
|-----------------|--------------------:|-------:|-----------------------------|
| Fireball        | 8d6 fire            | 150 ft | 20-foot-radius sphere       |
| Cone of Cold    | 8d8 cold            | Self   | 60-foot cone                |
| Lightning Bolt  | Not found in SRD    | —      | —                           |
```

Note the model honestly reports "Not found" when evidence is missing rather than fabricating — that's the prompt's no-hallucination discipline working.

## Running it

```bash
git clone https://github.com/<your-username>/research-agent-workshop
cd research-agent-workshop
uv sync
echo "OPENAI_API_KEY=sk-..." > .env
uv run main.py -q "How much damage does a Fireball deal?"
```

Add `--compact` for terse logs.

## Project layout

```
workshop/         my implementation
  harness.py      agentic loop, tool dispatch, memory turns
  agent.py        search + delegate_research tools, create_agent factory
  prompt.py       system + subagent prompts (delegation section tightened)
  search_in_docs.py   markdown KB search backend (workshop helper, unchanged)
  custom_logs.py      thread-safe logger (workshop helper, unchanged)
knowledge_base/   D&D 5e SRD markdown corpus
main.py           Click CLI entry point
pyproject.toml    uv-managed deps: datapizza-ai, click, rapidfuzz
```

## Credit

Workshop skeleton, SRD corpus, prompt scaffolds, and search backend by [raul-singh](https://github.com/raul-singh/research-agent-workshop). I implemented the `workshop/` package end-to-end and added the hardening, prompt engineering, and fixes described above.
