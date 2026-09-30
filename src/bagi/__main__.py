"""Implements bagi CLI."""

import logging
import pathlib

import click
import fsspec
import mfusepy as fuse
import uvicorn

import bagi
import bagi.fshttp
import bagi.fsspecfuse
import bagi.index_bag

CONTEXT_SETTINGS = {"show_default": True}


def get_logger() -> logging.Logger:
    return logging.getLogger("bagi")


@click.group(
    invoke_without_command=True,
    context_settings=CONTEXT_SETTINGS,
    help=(f"BAGI CLI for bagit zip index.\nVersion: {bagi.__version__}"),
)
@click.option("-l", "--loglevel", default="INFO", help="Set the logging level (INFO)")
@click.option("--version", is_flag=True, help="Show version and exit.")
@click.pass_context
def main(ctx: click.Context, loglevel: str, version: bool) -> None:
    """BAGI CLI."""
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
    """Create an index.parquet file an store in the zip."""
    _L = get_logger()
    nrows = bagi.index_bag.create_parquet_index(source)
    _L.info("Index created with %s rows.", nrows)


@main.command("mount")
@click.argument("source", type=click.Path(path_type=pathlib.Path, file_okay=True))
@click.argument("mountpoint", type=click.Path(path_type=pathlib.Path, file_okay=False))
@click.option("-f", "--foreground", is_flag=True, help="Mount as foreground process")
def mount_container(source, mountpoint, foreground) -> None:
    """Mount a zip container as a local file system."""
    fs = fsspec.filesystem("zip", fo=source, mode="r")
    fuse.FUSE(
        bagi.fsspecfuse.FSSpecFUSE(fs), str(mountpoint), foreground=foreground, ro=True
    )


@main.command("serve")
@click.argument("source", type=click.Path(path_type=pathlib.Path, file_okay=True))
@click.option("--pid", default="id", help="Base path for content.")
def serve_http(source, pid) -> None:
    fs = fsspec.filesystem("zip", fo=source, mode="r")

    # TODO: the geo part really should be a property of the file system, then it would
    #       be available as a "special" file when mounted as well.
    app_instance = bagi.fshttp.create_app(pid, fs)
    uvicorn.run(
        app_instance,
        host="127.0.0.1",
        port=8888,
    )
