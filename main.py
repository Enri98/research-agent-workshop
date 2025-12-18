import click

from ready_implementation.agent import create_agent


@click.command()
@click.option(
    "--query",
    "-q",
    prompt="Ask about D&D 5e",
    help="Your question about D&D 5e rules, spells, monsters, etc.",
)
def main(query: str) -> None:
    """D&D 5e SRD Knowledge Base Agent.

    Ask questions about D&D 5e rules, spells, monsters, items, classes, and more.
    The agent will search the SRD documents to find accurate answers.
    """
    agent = create_agent()

    click.echo(click.style("\n🎲 Searching the D&D 5e SRD...\n", fg="cyan", bold=True))

    response = agent.run(query)

    click.echo(click.style("📜 Answer:", fg="green", bold=True))
    click.echo(response.text)


if __name__ == "__main__":
    main()
