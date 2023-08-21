#!/usr/bin/env python3

""" Sets machine's ethernet network config (using dhcpcd5) """

import argparse
import logging
import pathlib
import re
import sys
import time

from offspot_runtime.__about__ import __version__
from offspot_runtime.checks import is_valid_ethernet_config
from offspot_runtime.configlib import (
    SYSTEMCTL_PATH,
    Config,
    ensure_folder,
    fail_error,
    fail_invalid,
    get_progname,
    simple_run,
    succeed,
    warn_unless_root,
)

NAME = pathlib.Path(__file__).stem
NETWORK_TYPES = ("dhcp", "static")
DHCPCD_CONF_PATH = pathlib.Path("/etc/dhcpcd.conf")
ARMOR_START = "### config-network: start ###"
ARMOR_END = "### config-network: stop ###"
Config.init(NAME)
logger = Config.logger


def ensure_dhcpcd_conf_armor(dhcpcd_conf_path: pathlib.Path) -> bool:
    """whether an armor was added to dhcpcd_conf_path file

    Looks for armor in file, adding one at bottom if missing
    Should the file not have an `interface` line, adds one for eth0 as well"""
    lines = dhcpcd_conf_path.read_text().splitlines()
    has_start = ARMOR_START in lines
    has_end = ARMOR_END in lines
    has_iface = "interface" in [re.split(r"\s", line)[0].strip() for line in lines]

    if has_start and has_end:
        if lines.index(ARMOR_START) < lines.index(ARMOR_END) and has_iface:
            return False
        lines.remove(ARMOR_START)
        lines.remove(ARMOR_END)
    elif has_start:
        lines.remove(ARMOR_START)
    elif has_end:
        lines.remove(ARMOR_END)

    if not has_iface:
        lines.append("interface eth0")

    lines.append(ARMOR_START)
    lines.append(ARMOR_END)

    content = "\n".join(lines)
    logger.debug(f"Fixing armor for {DHCPCD_CONF_PATH}:\n{content}\n---")
    dhcpcd_conf_path.write_text(content)

    return True


def write_dhcpcd_conf(dhcpcd_conf_path: pathlib.Path, network_conf: str):
    """add network_conf to dhcpcd_conf_path in-between armor"""

    dhcpcd_conf = dhcpcd_conf_path.read_text()

    armor_start = "### config-network: start ###"
    armor_end = "### config-network: stop ###"
    lines = dhcpcd_conf.splitlines()
    start = lines.index(armor_start)
    stop = lines.index(armor_end) + 1

    ensure_folder(dhcpcd_conf_path.parent)
    new_lines = (
        lines[0:start]
        + [armor_start]
        + network_conf.splitlines()
        + [armor_end]
        + lines[stop:]
    )
    if lines[-1]:
        new_lines.append("")
    content = "\n".join(new_lines)
    logger.debug(f"Writting {DHCPCD_CONF_PATH}:\n{content}\n---")
    dhcpcd_conf_path.write_text(content)


def main(
    network_type: str,
    address: str,
    routers: list[str],
    dns: list[str],
) -> int:
    logging.info("Configuring network")
    warn_unless_root()

    check = is_valid_ethernet_config(
        network_type=network_type, address=address, routers=routers, dns=dns
    )
    if not check.passed:
        fail_invalid(check.help_text)

    if network_type == "static":
        network_conf = (
            f"static ip_address={address}/24\n"
            f"static routers={' '.join(routers)}\n"
            f"static domain_name_servers={' '.join(dns)}\n"
        )
    else:
        network_conf = "dhcp"

    if ensure_dhcpcd_conf_armor(DHCPCD_CONF_PATH):
        logger.warning("Fixed missing placeholder in {DHCPCD_CONF_PATH}")

    try:
        write_dhcpcd_conf(DHCPCD_CONF_PATH, network_conf)
    except ValueError as exc:
        fail_error(f"Missing placeholder in {DHCPCD_CONF_PATH}: {exc}")

    if simple_run([str(SYSTEMCTL_PATH), "--no-pager", "restart", "dhcpcd"]) != 0:
        return 1

    # make sure we return once network conf has been applied
    logger.debug("sleeping a few seconds to hopefuly return after dhcpcd applied")
    time.sleep(5)
    return succeed("ethernet configuration applied")


def entrypoint():
    parser = argparse.ArgumentParser(
        prog=get_progname(),
        description="Configure Offspot's ethernet network",
    )
    parser.add_argument("-V", "--version", action="version", version=__version__)
    parser.add_argument("--debug", action="store_true", dest="debug")

    parser.add_argument(
        "--type",
        help="Network configuration type.",
        choices=NETWORK_TYPES,
        dest="network_type",
        required=True,
    )

    parser.add_argument(
        "--address",
        help="IP address to use",
        dest="address",
    )

    parser.add_argument(
        "--routers",
        help="IP to router gateway",
        dest="routers",
        default=[],
        required=False,
        action="append",
    )
    parser.add_argument(
        "--dns",
        help="IP(s) to dns servers. Space separated",
        dest="dns",
        default=[],
        required=False,
        action="append",
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
