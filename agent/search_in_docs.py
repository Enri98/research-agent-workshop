import re
from bisect import bisect_right
from pathlib import Path

import click
from rapidfuzz import fuzz


def search_in_doc(
    query: str,
    doc_path: str | Path,
    surrounding: int = 100,
    after_only: bool = False,
    fuzzy: bool = False,
) -> list[dict[str, str]]:
    """Search for query in a single document.

    Args:
        query: The search string (supports regex).
        doc_path: The path to the document to search (mandatory).
        surrounding: Number of characters before and after the match to include (default: 100).
        after_only: If True, only include characters after the match, not before (default: False).
        fuzzy: If True, use fuzzy search to find similar text (default: False).

    Returns:
        A list of dicts, each containing:
            - "source": The document filename
            - "content": The matched text with surrounding context
            - "match": The exact matched text
            - "title_path": Markdown heading path for the match location
    """
    results: list[dict[str, str]] = []
    file_path = Path(doc_path)

    # TODO: Check if the file exists, return empty results if not

    # TODO: Compile the query as a regex pattern (case insensitive)
    # If the query is not valid regex, escape it first
    pattern = ...

    # TODO: Read the file content

    # TODO: Build the heading index for title path extraction
    heading_index = ...

    # TODO: Find matches - either fuzzy or regex based on the fuzzy flag
    # Each match should be a tuple of (start_position, end_position, matched_text)
    match_spans = ...

    # TODO: For each match, extract context with surrounding characters
    # - If after_only is True, start from match_start
    # - Otherwise, start from max(0, match_start - surrounding)
    # - End at min(len(content), match_end + surrounding)
    # - Add ellipsis if content was truncated

    # TODO: Append result dict with source, content, match, and title_path

    return results


def search_in_documents(
    query: str,
    document: str | None = None,
    folder: str = "knowledge_base/docs",
    surrounding: int = 100,
    after_only: bool = False,
    fuzzy: bool = False,
) -> list[dict[str, str]]:
    """Search for query in documents and return matches with surrounding context.

    Args:
        query: The search string (supports regex).
        document: Optional specific document filename to search. If None, searches all .md files in folder.
        folder: Folder path containing documents to search (default: "knowledge_base/docs").
        surrounding: Number of characters before and after the match to include (default: 100).
        after_only: If True, only include characters after the match, not before (default: False).
        fuzzy: If True, use fuzzy search to find similar text (default: False).

    Returns:
        A list of dicts, each containing:
            - "source": The document filename
            - "content": The matched text with surrounding context
            - "match": The exact matched text
            - "title_path": Markdown heading path for the match location
    """
    folder_path = Path(folder)

    # TODO: If a specific document is provided:
    #   - Build the path to that document
    #   - Try adding .md extension if file doesn't exist
    #   - Call search_in_doc and return results

    # TODO: If no document specified:
    #   - Iterate over all .md files in the folder (sorted)
    #   - Call search_in_doc for each file
    #   - Collect and return all results

    return []


def _build_heading_index(content: str) -> tuple[list[int], list[str]]:
    """Precompute markdown heading positions with their hierarchical paths.

    This function scans the content for markdown headings (# to ######) and
    builds an index that maps positions to heading paths like "Chapter > Section > Subsection".

    Args:
        content: The full text content to scan for headings.

    Returns:
        A tuple of (positions, paths) where:
            - positions: List of character positions where headings start
            - paths: List of hierarchical heading paths at those positions
    """
    # TODO: Create a regex pattern to match markdown headings
    # Pattern should match lines starting with 1-6 # characters followed by text
    heading_pattern = ...

    stack: list[tuple[int, str]] = []  # Stack of (level, title) for building hierarchy
    positions: list[int] = []
    paths: list[str] = []

    # TODO: For each heading match:
    #   - Get the heading level (count of # characters)
    #   - Get the heading title text
    #   - Pop items from stack that are at same or deeper level
    #   - Push current heading to stack
    #   - Build path by joining all stack titles with " > "
    #   - Record position and path

    return positions, paths


def _find_title_path(position: int, heading_index: tuple[list[int], list[str]]) -> str:
    """Return the latest heading path occurring before the given position.

    Args:
        position: Character position in the document.
        heading_index: Tuple of (positions, paths) from _build_heading_index.

    Returns:
        The heading path string, or empty string if no heading precedes the position.
    """
    positions, paths = heading_index

    # TODO: Handle empty positions list

    # TODO: Use bisect_right to find the insertion point
    # The heading we want is at index (insertion_point - 1)

    # TODO: Return the path at that index, or empty string if index < 0

    return ""


def _fuzzy_find_matches(
    query: str,
    content: str,
    fuzzy_threshold: float = 85.0,
    max_fuzzy_matches_per_block: int = 5,
    paragraph_pattern: re.Pattern[str] = re.compile(r".+?(?:\n\s*\n|$)", re.DOTALL),
) -> list[tuple[int, int, str]]:
    """Find approximate matches for query inside content.

    Args:
        query: The search query to find approximately.
        content: The text content to search in.
        fuzzy_threshold: Minimum similarity score (0-100) for a match (default: 85.0).
        max_fuzzy_matches_per_block: Maximum matches to find per paragraph (default: 5).
        paragraph_pattern: Regex pattern to split content into blocks.

    Returns:
        List of (start_position, end_position, matched_text) tuples.
    """
    matches: list[tuple[int, int, str]] = []
    normalized_query = query.strip()

    # TODO: Return empty list if query is empty after stripping

    query_norm = normalized_query.lower()

    # TODO: For each paragraph/block in content:
    #   - Skip empty blocks
    #   - Use fuzz.partial_ratio_alignment to find fuzzy matches
    #   - If alignment score >= threshold, record the match
    #   - Replace matched portion with spaces to find additional matches
    #   - Stop when max matches reached or no more matches found

    return matches


@click.command()
@click.argument("query")
@click.option(
    "--document",
    "-d",
    help="Specific document to search (searches all if not provided)",
)
@click.option(
    "--folder",
    "-f",
    default="knowledge_base/docs",
    help="Folder containing documents to search",
)
@click.option(
    "--surrounding",
    "-s",
    default=100,
    type=int,
    help="Characters of context before/after match",
)
@click.option(
    "--after-only",
    "-a",
    is_flag=True,
    help="Only include characters after the match, not before",
)
@click.option(
    "--fuzzy",
    is_flag=True,
    help="Enable fuzzy search to find approximate matches",
)
def main(
    query: str,
    document: str | None,
    folder: str,
    surrounding: int,
    after_only: bool,
    fuzzy: bool,
) -> None:
    """Search for QUERY in markdown documents."""
    results = search_in_documents(
        query=query,
        document=document,
        folder=folder,
        surrounding=surrounding,
        after_only=after_only,
        fuzzy=fuzzy,
    )

    if not results:
        click.echo("No matches found.")
        return

    click.echo(f"Found {len(results)} match(es):\n")

    for i, result in enumerate(results, start=1):
        click.echo(click.style(f"[{i}] {result['source']}", fg="cyan", bold=True))
        click.echo(f"    Match: {click.style(result['match'], fg='yellow')}")
        click.echo(f"    Context: {result['content']}")
        click.echo()


if __name__ == "__main__":
    main()

