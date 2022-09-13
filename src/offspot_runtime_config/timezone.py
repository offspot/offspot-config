#!/usr/bin/env python3

""" Sets machine's timezone (using systemd) """

import argparse
import inspect
import logging
import pathlib
import re
import sys
from typing import Optional

parent = pathlib.Path(inspect.getfile(inspect.currentframe())).parent.resolve()
if parent not in sys.path:
    sys.path.insert(0, str(parent))

from offspot_config_lib import (  # noqa: E402
    Config,
    __version__,
    fail_invalid,
    simple_run,
    succeed,
    warn_unless_root,
)

NAME = pathlib.Path(__file__).stem
RE_TIMEZONE = re.compile(r"^([a-zA-Z0-9\-\_\/]){1,80}$")
Config.init(NAME)
logger = Config.logger


def main(timezone: str, debug: Optional[bool] = None) -> int:
    logging.info(f"Configuring timezone for `{timezone}`")
    warn_unless_root()

    if not RE_TIMEZONE.match(timezone):
        fail_invalid(f"Invalid timezone format “{timezone}”")

    rc = simple_run(
        ["/usr/bin/timedatectl", "--no-ask-password", "set-timezone", timezone]
    )
    if rc != 0:
        return 1
    succeed("Timezone applied")


def entrypoint():
    parser = argparse.ArgumentParser(
        prog=NAME, description="Configure Offspot's timezone"
    )
    parser.add_argument("-V", "--version", action="version", version=__version__)
    parser.add_argument("--debug", action="store_true", dest="debug")

    parser.add_argument(
        help="Desired timezone. Must be valid timezone. "
        "See `timedatectl list-timezones` for a full list",
        dest="timezone",
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
