#!/usr/bin/env python3

""" Validates and writes a docker-compose payload """

import argparse
import logging
import pathlib
import sys

from offspot_runtime.__about__ import __version__
from offspot_runtime.checks import is_valid_compose
from offspot_runtime.configlib import (
    Config,
    ensure_folder,
    fail_invalid,
    from_yaml,
    get_progname,
    succeed,
    to_yaml,
    warn_unless_root,
)

NAME = pathlib.Path(__file__).stem
DEFAULT_COMPOSE_PATH = "/etc/docker/compose.yml"
Config.init(NAME)
logger = Config.logger


def main(src: str, dest: str) -> int:
    logging.info(f"Writing docker-compose file from {src}")
    warn_unless_root()

    dest_path: pathlib.Path = pathlib.Path(dest).expanduser().resolve()

    payload = ""
    if src == "-":
        if not sys.stdin.isatty():
            payload = "\n".join(line for line in sys.stdin)
        else:
            fail_invalid("Missing input on stdin")
    else:
        try:
            payload = pathlib.Path(src).read_text()
        except Exception as exc:
            fail_invalid(f"Unable to read compose from {src}: {exc}")

    try:
        compose = from_yaml(payload)
    except Exception as exc:
        fail_invalid(f"Unable to parse YAML compose: {exc}")
        compose = {}

    # make sure we have defined services
    check = is_valid_compose(compose, required_ports=[80])
    if not check.passed:
        fail_invalid(check.help_text)

    ensure_folder(dest_path.parent)
    dest_path.write_text(to_yaml(compose))

    return succeed("docker-compose configured")


def entrypoint():
    parser = argparse.ArgumentParser(
        prog=get_progname(), description="Configure Offspot's hostname"
    )
    parser.add_argument("-V", "--version", action="version", version=__version__)
    parser.add_argument("--debug", action="store_true", dest="debug")

    parser.add_argument(
        help="Filename to read docker-compose config from. `-` to read from stdin",
        dest="src",
    )

    parser.add_argument(
        "--dest",
        help=f"Where to write docker-compose to. Defaults to {DEFAULT_COMPOSE_PATH}",
        dest="dest",
        required=False,
        default=DEFAULT_COMPOSE_PATH,
    )

    kwargs = dict(parser.parse_args()._get_kwargs())
    Config.set_debug(enabled=kwargs.pop("debug", False))

    try:
        sys.exit(main(**kwargs))
    except Exception as exc:
        if Config.debug:
            logger.exception(exc)
        else:
            logger.error(exc)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(entrypoint())
