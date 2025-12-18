import os
from pathlib import Path

from datapizza.agents import Agent
from datapizza.clients.openai import OpenAIClient
from datapizza.tools import tool
from dotenv import load_dotenv

from agent.prompt import SYSTEM_PROMPT
from agent.search_in_docs import search_in_documents

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
    # TODO: Call search_in_documents with the provided arguments
    results = ...

    # TODO: Handle the case when no results are found
    # Return a message like "No matches found for the given query."

    # TODO: Format the results into a readable string
    # Each result should include:
    #   - Result number and source document
    #   - The matched text
    #   - The title path (if available)
    #   - The context around the match
    output_parts = []

    return "\n".join(output_parts)


def load_structure() -> str:
    """Load the knowledge base structure file."""
    # TODO: Read and return the contents of "knowledge_base/structure.txt"
    ...


def create_agent() -> Agent:
    """Create and configure the D&D knowledge base agent."""
    # TODO: Load the knowledge base structure
    structure = ...

    # TODO: Create an OpenAI client
    # Use the model "gpt-4.1" and get the API key from environment
    client = ...

    # TODO: Create and return an Agent with:
    #   - name: "dnd_kb_agent"
    #   - the client you created
    #   - system prompt formatted with the structure
    #   - the search tool
    agent = ...

    return agent

