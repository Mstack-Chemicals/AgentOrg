import click

from agentorg.version import __version__


@click.group()
def main():
    """agentorg — Multi-agent development system built on Claude Code."""
    pass


@main.command()
def init():
    """Initialise project files in the current directory."""
    from agentorg.init_flow import initialise

    initialise()


@main.command()
def run():
    """Validate objective.md, scaffold run, and hand off to CTO."""
    from agentorg.init_flow import run

    run()


@main.command()
def start():
    """Full flow: init, wait for objective.md, run, launch CTO."""
    from agentorg.init_flow import start

    start()


@main.command()
@click.argument("timestamp", required=False)
@click.option(
    "--from", "from_phase",
    type=click.Choice(
        ["research", "architect", "engineering", "devops"],
        case_sensitive=False,
    ),
    default=None,
    help="Force restart from a specific phase (discards later artifacts).",
)
def resume(timestamp, from_phase):
    """Resume a previous run from where it stopped."""
    from agentorg.init_flow import resume as resume_fn

    resume_fn(timestamp=timestamp, from_phase=from_phase)


@main.command()
def doctor():
    """Check prerequisites and environment readiness."""
    from agentorg.init_flow import doctor

    doctor()


@main.command()
def version():
    """Print installed version."""
    click.echo(f"agentorg v{__version__}")
