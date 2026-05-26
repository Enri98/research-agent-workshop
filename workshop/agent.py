import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Annotated

from datapizza.clients.openai import OpenAIClient
from datapizza.tools import tool
from dotenv import load_dotenv

from workshop.custom_logs import log_event, log_task_done, log_task_failed, log_task_spawn
from workshop.harness import Agent
from workshop.prompt import SEARCH_GUIDANCE, SUBAGENT_PROMPT, SYSTEM_PROMPT
from workshop.search_in_docs import search_in_documents

load_dotenv()

MODEL = "gpt-5.4-mini"
MAX_SEARCH_RESULTS = 50
DEFAULT_TOOL_TIMEOUT = 60.0
SUBAGENT_TOOL_WORKERS = 4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE = PROJECT_ROOT / "knowledge_base"
TOC_PATH = KNOWLEDGE_BASE / "toc.txt"
DOCS_FOLDER = KNOWLEDGE_BASE / "docs"


@tool
def search(
    query: str,
    document: str | None = None,
    surrounding: int = 5,
    after_only: bool = False,
    fuzzy: bool = False,
    case_sensitive: bool = False,
) -> str:
    """Search the D&D 5e SRD knowledge base for information.

    Use this tool to find specific rules, spells, monsters, items, or any other
    D&D 5e content. The search supports regex patterns and returns matching text
    with surrounding context. Prefer exact search first for known terms, feature
    names, species names, spell names, and headings. If `fuzzy=True`, the same
    text-search rules still apply but with tolerance for typos and small wording
    differences; this is not semantic search and should not be used for
    open-ended questions, hypotheses, long natural-language descriptions, or
    already-exact terms like "Orc". If a heading search like "# Feature Name"
    fails, retry the bare feature name or the parent section heading instead.
    If the context gets truncated because of the `surrounding` value, that is
    indicated by an ellipsis.

    Args:
        query: The search string (supports regex). Be specific.
        document: Optional specific document filename to search (e.g.,
            "DND5eSRD_104-120.md"). If None, searches all documents.
        surrounding: Number of lines of context around each match (default: 5).
        after_only: If True, only include lines after the match, not before.
        fuzzy: If True, tolerate typos and small wording differences while still
            searching for a short concrete term or phrase. Use only after exact
            search fails due to likely spelling or wording mismatch. Not
            semantic search.
        case_sensitive: If True, match case exactly. Defaults to insensitive.

    Returns:
        Formatted search results with source document, matched text, optional
        heading path, and surrounding context.
    """
    results = search_in_documents(
        query=query,
        document=document,
        folder=str(DOCS_FOLDER),
        surrounding=surrounding,
        after_only=after_only,
        fuzzy=fuzzy,
        case_sensitive=case_sensitive,
    )

    if not results:
        return "No matches found for the given query."

    if len(results) > MAX_SEARCH_RESULTS:
        return (
            f"Search returned {len(results)} matches, which is too many to return at once. "
            "Narrow the query: set the `document` parameter to target a specific document, "
            "search for a more specific term or heading, or split into multiple smaller searches."
        )

    lines = [f"Found {len(results)} match(es):", ""]
    for i, result in enumerate(results, start=1):
        lines.append(f"[{i}] Source: {result['source']}")
        lines.append(f"    Match: {result['match']}")
        if result.get("title_path"):
            lines.append(f"    Title Path: {result['title_path']}")
        lines.append(f"    Context: {result['content']}")
        lines.append("")

    return "\n".join(lines)


@tool
def delegate_research(
    tasks: Annotated[
        list[str],
        "Concrete, independent research tasks. Each task should ask a subagent to gather evidence and sources, not merely plan the work.",
    ],
    max_parallel: Annotated[
        int,
        "Maximum number of subagents to run at the same time. Use 3-6 for broad comparisons.",
    ] = 4,
) -> str:
    """Delegate independent research tasks to parallel subagents.

    Each task is dispatched to its own subagent (named S1, S2, ...) running an
    isolated harness with only the `search` tool. The aggregated output is
    returned in the original task order so the caller can reference each
    finding by its index. Use this for 3+ independent research branches, broad
    comparisons across many options, or surveys whose individual context would
    otherwise overflow the main agent.

    Args:
        tasks: Concrete, independent research tasks. Each must be a
            self-contained instruction telling a subagent what evidence to
            gather and return. Empty or whitespace-only entries are dropped.
        max_parallel: Maximum number of subagents to run concurrently.

    Returns:
        Aggregated findings, one block per task, in original task order.
    """
    cleaned = [t.strip() for t in tasks if isinstance(t, str) and t.strip()]
    if not cleaned:
        return "No valid tasks provided to delegate."

    try:
        requested_workers = int(max_parallel)
    except (TypeError, ValueError):
        requested_workers = 4
    workers = max(1, min(requested_workers, len(cleaned), 8))

    subagent_prompt = format_subagent_prompt()
    log_event(
        "delegate",
        f"dispatching {len(cleaned)} task(s) with up to {workers} parallel subagent(s)",
    )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_run_subagent_task, task, i + 1, subagent_prompt)
            for i, task in enumerate(cleaned)
        ]
        results = [f.result() for f in futures]

    blocks = []
    for index, task, answer in results:
        if answer.startswith("<subagent error:"):
            blocks.append(f"[S{index}] FAILED — Task: {task}\nError: {answer}")
        else:
            blocks.append(f"[S{index}] Task: {task}\nAnswer: {answer}")
    return "\n\n".join(blocks)


def _run_subagent_task(
    task: str,
    index: int,
    system_prompt: str,
) -> tuple[int, str, str]:
    """Run a single delegated research task in an isolated harness Agent."""
    label = f"S{index}"
    log_task_spawn(label, task, tools=["search"], agent_name=label)

    start = time.monotonic()
    try:
        subagent = Agent(
            client=create_client(),
            system_prompt=system_prompt,
            tools=[search],
            name=label,
            max_tool_workers=SUBAGENT_TOOL_WORKERS,
            tool_timeout=DEFAULT_TOOL_TIMEOUT,
        )
        answer = subagent.run(task)
    except Exception as e:
        log_task_failed(label, time.monotonic() - start, e, agent_name=label)
        return (index, task, f"<subagent error: {type(e).__name__}: {e}>")

    log_task_done(label, time.monotonic() - start, agent_name=label)
    return (index, task, answer)


def load_structure() -> str:
    """Load the knowledge base table of contents file."""
    return TOC_PATH.read_text(encoding="utf-8")


def format_system_prompt() -> str:
    """Format the main agent system prompt with current KB structure."""
    return SYSTEM_PROMPT.format(
        structure=load_structure(),
        search_guidance=SEARCH_GUIDANCE,
    )


def format_subagent_prompt() -> str:
    """Format the delegated research subagent prompt with current KB structure."""
    return SUBAGENT_PROMPT.format(
        structure=load_structure(),
        search_guidance=SEARCH_GUIDANCE,
    )


def create_client() -> OpenAIClient:
    """Create the OpenAI client used by agents."""
    return OpenAIClient(
        model=MODEL,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def create_agent(compact_logs: bool = False) -> Agent:
    """Create and configure the D&D knowledge base agent."""
    return Agent(
        client=create_client(),
        system_prompt=format_system_prompt(),
        tools=[search, delegate_research],
        name="Main",
        tool_timeout=DEFAULT_TOOL_TIMEOUT,
        compact_logs=compact_logs,
    )
