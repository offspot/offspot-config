#!/usr/bin/env python3

""" Validates and writes a docker-compose payload """

import argparse
import inspect
import logging
import pathlib
import sys
from typing import Optional

parent = pathlib.Path(inspect.getfile(inspect.currentframe())).parent.resolve()
if parent not in sys.path:
    sys.path.insert(0, str(parent))

from offspot_config_lib import (  # noqa: E402
    Config,
    __version__,
    ensure_folder,
    fail_invalid,
    from_yaml,
    succeed,
    to_yaml,
    warn_unless_root,
)

NAME = pathlib.Path(__file__).stem
DEFAULT_COMPOSE_PATH = "/etc/docker/compose.yml"
Config.init(NAME)
logger = Config.logger


def main(src: str, dest: str, debug: Optional[bool]) -> int:
    logging.info(f"Writing docker-compose file from {src}")
    warn_unless_root()

    dest = pathlib.Path(dest).expanduser().resolve()

    if src == "-":
        if not sys.stdin.isatty():
            payload = "\n".join([line for line in sys.stdin])
        else:
            fail_invalid("Missing input on stdin")
    else:
        try:
            with open(pathlib.Path(src), "r") as fh:
                payload = fh.read()
        except Exception as exc:
            fail_invalid(f"Unable to read compose from {src}: {exc}")

    try:
        compose = from_yaml(payload)
    except Exception as exc:
        fail_invalid(f"Unable to parse YAML compose: {exc}")

    # make sure we have defined services
    services = compose.get("services", [])
    if not services or not isinstance(services, dict):
        fail_invalid("No `services` defined in your YAML payload")

    ensure_folder(dest.parent)
    with open(dest, "w") as fh:
        fh.write(to_yaml(compose))

    succeed("docker-compose configured")


def entrypoint():
    parser = argparse.ArgumentParser(
        prog=NAME, description="Configure Offspot's hostname"
    )
    parser.add_argument("-V", "--version", action="version", version=__version__)
    parser.add_argument("--debug", action="store_true", dest="debug")

    parser.add_argument(
        help="Filename to read docker-compose config from. `-` to read from stdin",
        dest="src",
    )

    parser.add_argument(
        "--dest",
        help="Where to write docker-compose to. " f"Defaults to {DEFAULT_COMPOSE_PATH}",
        dest="dest",
        required=False,
        default=DEFAULT_COMPOSE_PATH,
    )

    kwargs = dict(parser.parse_args()._get_kwargs())
    Config.set_debug(kwargs.get("debug"))

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
