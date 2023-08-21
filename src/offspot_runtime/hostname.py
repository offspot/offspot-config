#!/usr/bin/env python3

""" Sets machine's hostname (using systemd) """

import argparse
import logging
import pathlib
import re
import sys

from offspot_runtime.__about__ import __version__
from offspot_runtime.checks import is_valid_hostname
from offspot_runtime.configlib import (
    Config,
    fail_invalid,
    get_progname,
    simple_run,
    succeed,
    warn_unless_root,
)

NAME = pathlib.Path(__file__).stem

Config.init(NAME)
logger = Config.logger


def main(hostname: str) -> int:
    logging.info(f"Configuring hostname for `{hostname}`")
    warn_unless_root()

    check = is_valid_hostname(hostname)
    if not check.passed:
        fail_invalid(check.help_text)

    rc = simple_run(
        ["/usr/bin/hostnamectl", "--no-ask-password", "set-hostname", hostname]
    )
    if rc != 0:
        return 1

    hosts_path = pathlib.Path("/etc/hosts")
    hosts = hosts_path.read_text().splitlines()
    existing = False
    new_line = f"127.0.1.1\t{hostname}\n"
    for index, line in enumerate(list(hosts)):
        if re.match(r"^127.0.1.1", line):
            hosts[index] = new_line
            existing = True
    if not existing:
        hosts.append(new_line)
    hosts_path.write_text("".join(hosts))

    return succeed("hostname configured")


def entrypoint():
    parser = argparse.ArgumentParser(
        prog=get_progname(), description="Configure Offspot's hostname"
    )
    parser.add_argument("-V", "--version", action="version", version=__version__)
    parser.add_argument("--debug", action="store_true", dest="debug")

    parser.add_argument(
        help="Desired hostname. Must be valid domain (dot-separated, "
        "1-63 length of a-z, 0-9 and - chars up to a total of 255 chars",
        dest="hostname",
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
