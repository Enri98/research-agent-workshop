import sys

import click

from workshop.agent import create_agent

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


@click.command()
@click.option(
    "--query",
    "-q",
    prompt="Ask about D&D 5e",
    help="Your question about D&D 5e rules, spells, monsters, etc.",
)
@click.option(
    "--compact",
    is_flag=True,
    default=False,
    help="Compact log output (one line per event).",
)
def main(query: str, compact: bool) -> None:
    """D&D 5e SRD Knowledge Base Agent.

    Ask questions about D&D 5e rules, spells, monsters, items, classes, and more.
    The agent will search the SRD documents to find accurate answers.
    """
    agent = create_agent(compact_logs=compact)

    click.echo(click.style("\nD&D 5e SRD Research\n", fg="cyan", bold=True))

    response = agent.run(query)

    click.echo(click.style("Answer:", fg="green", bold=True))
    click.echo(response)


if __name__ == "__main__":
    main()
