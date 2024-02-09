#!/usr/bin/env python3

""" Toggle dnsmasq's spoof mode when internet connection is offline """

import argparse
import pathlib
import re
import subprocess
import sys

from offspot_runtime.__about__ import __version__
from offspot_runtime.configlib import (
    DNSMASQ_SPOOF_CONFIG_PATH,
    Config,
    ensure_folder,
    fail_error,
    get_progname,
    restart_service,
    succeed,
    warn_unless_root,
)

NAME = pathlib.Path(__file__).stem
INTERNET_STATUS_PATH = pathlib.Path("/var/run/internet")

Config.init(NAME)
logger = Config.logger


def toggle_dnsmasq(dnsmasq_conf_path: pathlib.Path, *, spoof: bool):
    """wether spoof file has been changed"""

    ensure_folder(dnsmasq_conf_path.parent)
    content = dnsmasq_conf_path.read_text()

    is_spoof = False
    for line in content.splitlines():
        if line.startswith("address=/#/"):
            is_spoof = True
            break

    if (spoof and is_spoof) or (not spoof and not is_spoof):
        logger.info(f"already in correct mode: {is_spoof=} {spoof=}")
        return False

    logger.info(f"toggling from {is_spoof=} into {spoof=}")

    # turning non-spoof into spoof by removing comment on address
    fixed_lines = []
    for line in content.splitlines():
        # keep manual comments as-is
        if line.startswith("##"):
            fixed_lines.append(line)
            continue

        # uncomment commented lines
        comment_match = re.match(r"^#\s(?P<line>.+)$", line)
        if comment_match:
            fixed_lines.append(comment_match.groupdict()["line"])
        else:
            fixed_lines.append(f"# {line}")

    dnsmasq_conf_path.write_text("\n".join(fixed_lines))

    return True


def restart_dnsmasq():
    return (
        subprocess.run(
            ["/usr/bin/systemctl", "restart", "dnsmasq"], check=False
        ).returncode
        == 0
    )


def main() -> int:
    warn_unless_root()

    spoof = False
    try:
        status = INTERNET_STATUS_PATH.read_text().strip()
        spoof = status != "online"
    except Exception as exc:
        fail_error(
            f"unable to read Internet connection status "
            f"from {INTERNET_STATUS_PATH}: {exc}"
        )
    try:
        fixed = toggle_dnsmasq(dnsmasq_conf_path=DNSMASQ_SPOOF_CONFIG_PATH, spoof=spoof)
    except Exception as exc:
        fail_error(
            "unable to read/write dnsmasq spoof config "
            f"at {DNSMASQ_SPOOF_CONFIG_PATH}: {exc}"
        )
        fixed = False
    if not fixed:
        return 0

    if restart_service("dnsmasq") != 0:
        fail_error("failed to restart dnsmasq")

    return succeed("toggled spoof mode")


def entrypoint():
    parser = argparse.ArgumentParser(
        prog=get_progname(),
        description="Toggle dnsmasq's spoof mode based on internet connectivity",
    )
    parser.add_argument("-V", "--version", action="version", version=__version__)
    parser.add_argument("--debug", action="store_true", dest="debug")

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
