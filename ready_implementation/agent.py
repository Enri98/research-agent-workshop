import os
from pathlib import Path

from datapizza.agents import Agent
from datapizza.clients.openai import OpenAIClient
from datapizza.tools import tool
from dotenv import load_dotenv

from agent.prompt import SYSTEM_PROMPT
from ready_implementation.search_in_docs import search_in_documents

load_dotenv()


@tool
def search(
    query: str,
    document: str | None = None,
    surrounding: int = 100,
    after_only: bool = False,
    fuzzy: bool = False,
) -> str:
    """Search the D&D 5e SRD knowledge base for information.

    Use this tool to find specific rules, spells, monsters, items, or any other
    D&D 5e content. The search supports regex patterns and returns matching text
    with surrounding context. If the text gets truncated because of the surrounding value,
    it is indicated by an ellipsis.

    Args:
        query: The search string (supports regex). Be specific with your search terms.
        document: Optional specific document filename to search (e.g., "DND5eSRD_104-120.md").
                  If None, searches all documents.
        surrounding: Number of characters of context to include around matches (default: 100).
        after_only: If True, only include characters after the match, not before.
        fuzzy: If True, find similar text when exact matches fail.

    Returns:
        Formatted search results with source document and matching content.
    """
    results = search_in_documents(
        query=query,
        document=document,
        surrounding=surrounding,
        after_only=after_only,
        fuzzy=fuzzy,
    )

    if not results:
        return "No matches found for the given query."

    output_parts = [f"Found {len(results)} match(es):\n"]

    for i, result in enumerate(results, start=1):
        output_parts.append(f"[{i}] Source: {result['source']}")
        output_parts.append(f"    Match: {result['match']}")
        if result.get("title_path"):
            output_parts.append(f"    Title Path: {result['title_path']}")
        output_parts.append(f"    Context: {result['content']}")
        output_parts.append("")

    return "\n".join(output_parts)


def load_structure() -> str:
    """Load the knowledge base structure file."""
    structure_path = Path("knowledge_base/structure.txt")
    return structure_path.read_text(encoding="utf-8")


def create_agent() -> Agent:
    """Create and configure the D&D knowledge base agent."""
    structure = load_structure()

    client = OpenAIClient(
        model="gpt-5.1",
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    agent = Agent(
        name="dnd_kb_agent",
        client=client,
        system_prompt=SYSTEM_PROMPT.format(structure=structure),
        tools=[search],
    )

    return agent
