"""Implements bagi CLI."""

import logging
import pathlib

import click

import bagi

CONTEXT_SETTINGS = {"show_default": True}


def get_logger() -> logging.Logger:
    return logging.getLogger("bagi")


@click.group(
    invoke_without_command=True,
    context_settings=CONTEXT_SETTINGS,
    help=(
        "BLOFS CLI for binary large object container indexing and access."
        f"\nVersion: {bagi.__version__}"
    ),
)
@click.option("-l", "--loglevel", default="INFO", help="Set the logging level (INFO)")
@click.option("--version", is_flag=True, help="Show version and exit.")
@click.pass_context
def main(ctx: click.Context, loglevel: str, version: bool) -> None:
    """BLOFS CLI."""
    if version:
        print(f"BLOFS version {bagi.__version__}")
        ctx.exit(0)
    ctx.ensure_object(dict)
    loglevel = loglevel.strip().upper()
    assert loglevel in ("DEBUG", "INFO", "ERROR", "WARNING", "CRITICAL")
    numeric_level = getattr(logging, loglevel)
    logging.basicConfig(level=numeric_level)
    logger = get_logger()
    logger.setLevel(numeric_level)


@main.command("index")
@click.argument("source", type=click.Path(path_type=pathlib.Path, file_okay=True))
def index_bag(source: pathlib.Path):
    msg = "index_bag"
    raise NotImplementedError(msg)
