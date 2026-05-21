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


@tool
def search(
    query: str,
    document: str | None = None,
    surrounding: int = 5,
    after_only: bool = False,
    fuzzy: bool = False,
    case_sensitive: bool = False,
) -> str:
    """Search the D&D 5e SRD knowledge base for information."""
    # TODO: Call search_in_documents with the provided arguments.
    # TODO: Return "No matches found for the given query." when empty.
    # TODO: If there are more than MAX_SEARCH_RESULTS, return a warning asking
    # the agent to narrow the query.
    # TODO: Format each result with source, match, optional title path, and context.
    raise NotImplementedError


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
    """Delegate independent research tasks to parallel subagents."""
    # TODO: Strip empty tasks and handle an empty task list.
    # TODO: Format the subagent prompt once with format_subagent_prompt().
    # TODO: Run _run_subagent_task for each task with ThreadPoolExecutor.
    # TODO: Preserve S1, S2, ... ordering in the final formatted output.
    raise NotImplementedError


def _run_subagent_task(
    task: str,
    index: int,
    system_prompt: str,
) -> tuple[int, str, str]:
    """Run a single delegated research task in an isolated harness Agent."""
    # TODO: Create a subagent named S{index} with only the search tool.
    # TODO: Log spawn, success, and failure with workshop.custom_logs.
    # TODO: Return (index, task, answer).
    raise NotImplementedError


def load_structure() -> str:
    """Load the knowledge base table of contents file."""
    structure_path = Path("knowledge_base/toc.txt")
    return structure_path.read_text(encoding="utf-8")


def format_system_prompt() -> str:
    """Format the main agent system prompt with current KB structure."""
    # TODO: Format SYSTEM_PROMPT with structure=load_structure() and
    # search_guidance=SEARCH_GUIDANCE.
    raise NotImplementedError


def format_subagent_prompt() -> str:
    """Format the delegated research subagent prompt with current KB structure."""
    # TODO: Format SUBAGENT_PROMPT with structure=load_structure() and
    # search_guidance=SEARCH_GUIDANCE.
    raise NotImplementedError


def create_client() -> OpenAIClient:
    """Create the OpenAI client used by agents."""
    return OpenAIClient(
        model=MODEL,
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def create_agent() -> Agent:
    """Create and configure the D&D knowledge base agent."""
    # TODO: Return a workshop.harness.Agent configured with create_client(),
    # format_system_prompt(), and the search/delegate_research tools.
    raise NotImplementedError
