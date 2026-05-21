import re
from bisect import bisect_right
from pathlib import Path

import click
from rapidfuzz import fuzz


def search_in_doc(
    query: str,
    doc_path: str | Path,
    surrounding: int = 5,
    after_only: bool = False,
    fuzzy: bool = False,
    case_sensitive: bool = False,
) -> list[dict[str, str]]:
    """Search for query in a single document.

    Args:
        query: The search string (supports regex).
        doc_path: The path to the document to search (mandatory).
        surrounding: Number of lines before and after the match to include (default: 5).
        after_only: If True, only include lines after the match, not before (default: False).
        fuzzy: If True, use fuzzy search to find similar text (default: False).
        case_sensitive: If True, match case exactly (default: False).

    Returns:
        A list of dicts, each containing:
            - "source": The document filename
            - "content": The matched text with surrounding context
            - "match": The exact matched text
            - "title_path": Markdown heading path for the match location
    """
    results: list[dict[str, str]] = []
    file_path = Path(doc_path)

    if not file_path.exists():
        return results

    regex_flags = 0 if case_sensitive else re.IGNORECASE
    try:
        pattern = re.compile(query, regex_flags)
    except re.error:
        # If query is not valid regex, escape it
        pattern = re.compile(re.escape(query), regex_flags)

    content = file_path.read_text(encoding="utf-8")
    heading_index = _build_heading_index(content)

    if fuzzy:
        match_spans = _fuzzy_find_matches(
            query,
            content,
            case_sensitive=case_sensitive,
        )
    else:
        match_spans = [
            (m.start(), m.end(), m.group()) for m in pattern.finditer(content)
        ]

    for match_start, match_end, matched_text in match_spans:
        context = _line_context(
            content=content,
            match_start=match_start,
            match_end=match_end,
            surrounding=surrounding,
            after_only=after_only,
        )

        results.append(
            {
                "source": file_path.name,
                "content": context,
                "match": matched_text,
                "title_path": _find_title_path(match_start, heading_index),
            }
        )

    return results


def search_in_documents(
    query: str,
    document: str | None = None,
    folder: str = "knowledge_base/docs",
    surrounding: int = 5,
    after_only: bool = False,
    fuzzy: bool = False,
    case_sensitive: bool = False,
) -> list[dict[str, str]]:
    """Search for query in documents and return matches with surrounding context.

    Args:
        query: The search string (supports regex).
        document: Optional specific document filename to search. If None, searches all .md files in folder.
        folder: Folder path containing documents to search (default: "knowledge_base/docs").
        surrounding: Number of lines before and after the match to include (default: 5).
        after_only: If True, only include lines after the match, not before (default: False).
        fuzzy: If True, use fuzzy search to find similar text (default: False).
        case_sensitive: If True, match case exactly (default: False).

    Returns:
        A list of dicts, each containing:
            - "source": The document filename
            - "content": The matched text with surrounding context
            - "match": The exact matched text
            - "title_path": Markdown heading path for the match location
    """
    folder_path = Path(folder)

    # Search in single document or all documents in folder
    if document:
        doc_path = folder_path / document
        if not doc_path.exists():
            # Try with .md extension
            doc_path = folder_path / f"{document}.md"
        return search_in_doc(
            query=query,
            doc_path=doc_path,
            surrounding=surrounding,
            after_only=after_only,
            fuzzy=fuzzy,
            case_sensitive=case_sensitive,
        )
    else:
        results: list[dict[str, str]] = []
        for file_path in sorted(folder_path.glob("*.md")):
            results.extend(
                search_in_doc(
                    query=query,
                    doc_path=file_path,
                    surrounding=surrounding,
                    after_only=after_only,
                    fuzzy=fuzzy,
                    case_sensitive=case_sensitive,
                )
            )
        return results


def _build_heading_index(content: str) -> tuple[list[int], list[str]]:
    """Precompute markdown heading positions with their hierarchical paths."""
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    stack: list[tuple[int, str]] = []
    positions: list[int] = []
    paths: list[str] = []

    for heading in heading_pattern.finditer(content):
        level = len(heading.group(1))
        title = heading.group(2).strip()

        while stack and stack[-1][0] >= level:
            stack.pop()

        stack.append((level, title))
        path = " > ".join(item for _, item in stack)
        positions.append(heading.start())
        paths.append(path)

    return positions, paths


def _find_title_path(position: int, heading_index: tuple[list[int], list[str]]) -> str:
    """Return the latest heading path occurring before the given position."""
    positions, paths = heading_index
    if not positions:
        return ""

    idx = bisect_right(positions, position) - 1
    if idx < 0:
        return ""

    return paths[idx]


def _line_context(
    content: str,
    match_start: int,
    match_end: int,
    surrounding: int,
    after_only: bool,
) -> str:
    """Return whole-line context around a match span."""
    lines = content.splitlines(keepends=True)
    if not lines:
        return ""

    line_starts: list[int] = []
    position = 0
    for line in lines:
        line_starts.append(position)
        position += len(line)

    match_start_line = max(0, bisect_right(line_starts, match_start) - 1)
    match_end_position = max(match_start, match_end - 1)
    match_end_line = max(0, bisect_right(line_starts, match_end_position) - 1)

    context_start_line = (
        match_start_line if after_only else max(0, match_start_line - surrounding)
    )
    context_end_line = min(len(lines), match_end_line + surrounding + 1)
    context = "".join(lines[context_start_line:context_end_line])

    if context_start_line > 0 and not after_only:
        context = "..." + context
    if context_end_line < len(lines):
        context = context + "..."

    return context


def _fuzzy_find_matches(
    query: str,
    content: str,
    fuzzy_threshold: float = 85.0,
    max_fuzzy_matches_per_block: int = 5,
    paragraph_pattern: re.Pattern[str] = re.compile(r".+?(?:\n\s*\n|$)", re.DOTALL),
    case_sensitive: bool = False,
) -> list[tuple[int, int, str]]:
    """Find approximate matches for query inside content."""
    matches: list[tuple[int, int, str]] = []
    normalized_query = query.strip()
    if not normalized_query:
        return matches

    query_norm = normalized_query if case_sensitive else normalized_query.casefold()

    for block in paragraph_pattern.finditer(content):
        segment = block.group()
        if not segment.strip():
            continue

        working_norm = segment if case_sensitive else segment.casefold()
        match_count = 0

        while match_count < max_fuzzy_matches_per_block:
            alignment = fuzz.partial_ratio_alignment(query_norm, working_norm)
            if alignment.score < fuzzy_threshold:
                break

            relative_start = alignment.dest_start
            relative_end = alignment.dest_end
            abs_start = block.start() + relative_start
            abs_end = block.start() + relative_end
            matched_text = content[abs_start:abs_end].strip()
            if not matched_text:
                matched_text = segment.strip()

            matches.append((abs_start, abs_end, matched_text))
            match_count += 1

            replacement = " " * (relative_end - relative_start)
            working_norm = (
                working_norm[:relative_start]
                + replacement
                + working_norm[relative_end:]
            )

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
    default=5,
    type=int,
    help="Lines of context before/after match",
)
@click.option(
    "--after-only",
    "-a",
    is_flag=True,
    help="Only include lines after the match, not before",
)
@click.option(
    "--fuzzy",
    is_flag=True,
    help="Enable fuzzy search to find approximate matches",
)
@click.option(
    "--case-sensitive",
    is_flag=True,
    help="Match case exactly instead of the default case-insensitive search",
)
def main(
    query: str,
    document: str | None,
    folder: str,
    surrounding: int,
    after_only: bool,
    fuzzy: bool,
    case_sensitive: bool,
) -> None:
    """Search for QUERY in markdown documents."""
    results = search_in_documents(
        query=query,
        document=document,
        folder=folder,
        surrounding=surrounding,
        after_only=after_only,
        fuzzy=fuzzy,
        case_sensitive=case_sensitive,
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
