import asyncio
import os
import time
from pathlib import Path
from typing import Annotated

from datapizza.agents import Agent
from datapizza.clients.openai import OpenAIClient
from datapizza.tools import tool
from dotenv import load_dotenv

from agent.custom_logs import (
    log_delegate_start,
    log_delegate_task,
    log_subagent_done,
    log_subagent_failed,
    log_subagent_response,
    log_subagent_spawn,
    log_tool_call,
    log_tool_output,
    reset_context,
    set_subagent_context,
)
from agent.prompt import SEARCH_GUIDANCE, SUBAGENT_PROMPT, SYSTEM_PROMPT
from agent.search_in_docs import search_in_documents

load_dotenv()

MODEL = "gpt-5.4"
MAX_SEARCH_RESULTS = 50


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
    names, species names, spell names, and headings. If fuzzy=True, the same
    text-search rules still apply, but with tolerance for typos and small wording
    differences. Fuzzy search is not semantic search and should not be used for
    open-ended questions, hypotheses, long natural-language descriptions, or
    already-exact terms like "Orc". If a heading search like "# Feature Name"
    fails, retry the bare feature name or the parent section heading instead.
    If the text gets truncated because of the surrounding value, it is indicated
    by an ellipsis.

    Args:
        query: The search string (supports regex). Be specific with your search terms.
        document: Optional specific document filename to search (e.g., "DND5eSRD_104-120.md").
                  If None, searches all documents.
        surrounding: Number of lines of context to include around matches (default: 5).
        after_only: If True, only include lines after the match, not before.
        fuzzy: If True, tolerate typos and small wording differences while still
               searching for a short concrete term or phrase. Use only after
               exact search fails due likely spelling/wording mismatch. Not
               semantic search.
        case_sensitive: If True, match case exactly. Defaults to case-insensitive search.

    Returns:
        Formatted search results with source document and matching content.
    """
    log_tool_call(
        "search",
        query=query,
        document=document,
        surrounding=surrounding,
        after_only=after_only,
        fuzzy=fuzzy,
        case_sensitive=case_sensitive,
    )

    results = search_in_documents(
        query=query,
        document=document,
        surrounding=surrounding,
        after_only=after_only,
        fuzzy=fuzzy,
        case_sensitive=case_sensitive,
    )

    if not results:
        output = "No matches found for the given query."
        log_tool_output("search", output)
        return output

    if len(results) > MAX_SEARCH_RESULTS:
        output = (
            f"Search returned {len(results)} matches, which is too many to return safely. "
            "Narrow the query before trying again: use a more specific term, set the "
            "document parameter when possible, search a heading/title first, or split the "
            "question into smaller searches."
        )
        log_tool_output("search", output)
        return output

    output_parts = [f"Found {len(results)} match(es):\n"]

    for i, result in enumerate(results, start=1):
        output_parts.append(f"[{i}] Source: {result['source']}")
        output_parts.append(f"    Match: {result['match']}")
        if result.get("title_path"):
            output_parts.append(f"    Title Path: {result['title_path']}")
        output_parts.append(f"    Context: {result['content']}")
        output_parts.append("")

    output = "\n".join(output_parts)
    log_tool_output("search", output)
    return output


async def _run_subagent_task(
    task: str,
    index: int,
    structure: str,
) -> str:
    """Run a single research task in an isolated subagent."""
    started_at = time.monotonic()
    log_subagent_spawn(index, task)
    token = set_subagent_context(index, task)
    subagent = Agent(
        name=f"dnd_kb_research_subagent_{index}",
        client=create_client(),
        system_prompt=SUBAGENT_PROMPT.format(
            structure=structure,
            search_guidance=SEARCH_GUIDANCE,
        ),
        tools=[search],
        max_steps=20,
    )
    try:
        result = await subagent.a_run(task)
    except Exception as exc:
        log_subagent_failed(index, time.monotonic() - started_at, exc)
        raise
    finally:
        reset_context(token)

    log_subagent_done(index, time.monotonic() - started_at)
    if not result or not result.text:
        answer = "No answer returned."
        log_subagent_response(index, answer)
        return answer

    log_subagent_response(index, result.text)
    return result.text


@tool
async def delegate_research(
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

    Use this before direct search when a question has three or more independent
    research branches, such as comparing many options or surveying multiple rules
    areas. Each task should be self-contained and ask for concise findings with
    source documents. Subagents can use search but cannot delegate to other agents.

    Args:
        tasks: Independent research tasks to run in parallel.
        max_parallel: Maximum number of subagents to run at the same time.

    Returns:
        Numbered subagent findings, one section per task.
    """
    log_tool_call("delegate_research", tasks=tasks, max_parallel=max_parallel)

    cleaned_tasks = [task.strip() for task in tasks if task.strip()]
    if not cleaned_tasks:
        output = "No research tasks provided."
        log_tool_output("delegate_research", output)
        return output

    structure = load_structure()
    concurrency = min(max(1, max_parallel), 8)
    log_delegate_start(len(cleaned_tasks), max_parallel, concurrency)
    for index, task in enumerate(cleaned_tasks, start=1):
        log_delegate_task(index, task)

    semaphore = asyncio.Semaphore(concurrency)

    async def run_limited(index: int, task: str) -> tuple[int, str, str]:
        async with semaphore:
            try:
                answer = await _run_subagent_task(task, index, structure)
            except Exception as exc:
                answer = f"Subagent failed: {exc}"
            return index, task, answer

    results = await asyncio.gather(
        *(run_limited(index, task) for index, task in enumerate(cleaned_tasks, start=1))
    )

    output_parts = [f"Completed {len(results)} delegated research task(s):"]
    for index, task, answer in sorted(results):
        output_parts.append("")
        output_parts.append(f"[{index}] Task: {task}")
        output_parts.append(answer)

    output = "\n".join(output_parts)
    log_tool_output("delegate_research", output)
    return output


def load_structure() -> str:
    """Load the knowledge base structure file."""
    structure_path = Path("knowledge_base/structure.txt")
    return structure_path.read_text(encoding="utf-8")


def create_client() -> OpenAIClient:
    """Create the OpenAI client used by agents."""
    return OpenAIClient(
        model=MODEL,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def create_agent() -> Agent:
    """Create and configure the D&D knowledge base agent."""
    structure = load_structure()

    client = create_client()
    agent = Agent(
        name="dnd_kb_agent",
        client=client,
        system_prompt=SYSTEM_PROMPT.format(
            structure=structure,
            search_guidance=SEARCH_GUIDANCE,
        ),
        tools=[search, delegate_research],
    )

    return agent
