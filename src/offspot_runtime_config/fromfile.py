#!/usr/bin/env python3

""" Configures boot-time setable settings from /boot/config.json

    Using individual scripts for various features ; each reporting whether
    requested setting is valid, and set (or errored) or ignored.
    JSON config file is rewritten to remove applied setting """
import argparse
import inspect
import pathlib
import sys
from typing import Dict, Optional

parent = pathlib.Path(inspect.getfile(inspect.currentframe())).parent.resolve()
if parent not in sys.path:
    sys.path.insert(0, str(parent))

from offspot_config_lib import (  # noqa: E402
    IPTABLES_DIR,
    SYSTEMCTL_PATH,
    Config,
    __version__,
    colored,
    from_yaml,
    get_bin,
    restart_service,
    simple_run,
    succeed,
    to_yaml,
    warn_unless_root,
)

NAME = pathlib.Path(__file__).stem
DEFAULT_CONFIG_PATH = pathlib.Path("/boot/offspot.yaml")
Config.init(NAME)
logger = Config.logger
banner = """# This file allows changing this Offspot's configuration on boot.
###########################
# It is **NOT** recommended to edit this file manually.
###########################
# Documentation about this file at: https://github.com/offspot/runtime-config
# It **must** remain a valid YAML (single) document
#
# It is not a Configuration Reference.
# It's a request for change.
# On regular boots, this file should be empty.
# On first boot, it would be full, including containers configuration.
#
# Samples of top-level keys/features:
# --------
#
#
# ethernet:
#   type: dhcp
#
# ethernet:
#   type: static
#   address: 192.168.5.10
#   routers:
#   - 192.168.5.200
#   dns:
#   - 192.168.5.200
#   - 1.1.1.1
#
# hostname: emmet
#
# timezone: UTC
#
# timezone: Asia/Taipei
#
# # scenario A: Hotspot-only
# ap:
#   ssid: Welcome WiFi
#
# # scenario B: internet relay (sharing ethernet connexion along offspot)
# ap:
#   ssid: Welcome WiFi
#   as-gateway: true
#
# # scenario C: WiFi+wired hotspot
# # you'll need to configure static ethernet for this one
# ap:
#   ssid: Welcome WiFi
#   passphrase: this is secret
#   other-interfaces:
#   - eth0
#
# # scenario D: Hotspot + existing LAN
# # Offspot available via WiFi and on existing LAN
# ap:
#   ssid: Welcome WiFi
#   nodhcp-interfaces:
#   - eth0
"""


class Handlers:
    @staticmethod
    def config_hostname(item: str, debug: bool) -> int:
        command = get_bin("hostname")
        if debug:
            command += ["--debug"]
        command += [item]
        return simple_run(command)

    @staticmethod
    def config_timezone(item: str, debug: bool) -> int:
        command = get_bin("timezone")
        if debug:
            command += ["--debug"]
        command += [item]
        return simple_run(command)

    @staticmethod
    def config_ethernet(item: Dict, debug: bool) -> int:
        if not isinstance(item, dict):
            return 2

        command = get_bin("ethernet")
        if debug:
            command += ["--debug"]
        for key in ("type", "address"):
            if item.get(key):
                command += [f"--{key}", item.get(key)]

        for key in ("routers", "dns"):
            option = item.get(key)
            if option and isinstance(option, list):
                for entry in option:
                    command += [f"--{key}", entry]

        return simple_run(command)

    @staticmethod
    def config_ap(item: Dict, debug: bool) -> int:
        if not isinstance(item, dict):
            return 2

        if not item.get("ssid"):
            return 2

        command = get_bin("ap")

        if debug:
            command += ["--debug"]

        for key in (
            "passphrase",
            "address",
            "tld",
            "domain",
            "welcome",
            "channel",
            "country",
            "interface",
            "dhcp-range",
            "network",
        ):
            if item.get(key) is not None:
                command += [f"--{key}", str(item.get(key))]

        for key in ("hide", "as-gateway", "spoof"):
            if item.get(key):
                command += [f"--{key}"]

        for key in (
            "dns",
            "other-interfaces",
            "except-interfaces",
            "nodhcp-interfaces",
        ):
            option = item.get(key)
            if option and isinstance(option, list):
                for entry in option:
                    command += [f"--{key}", entry]

        command += [item.get("ssid")]
        return simple_run(command)

    @staticmethod
    def config_containers(item: Dict, debug: bool) -> int:
        payload = to_yaml(item)
        command = get_bin("containers")
        if debug:
            command += ["--debug"]
        command += ["-"]
        return simple_run(command, stdin=payload)


def restore_iptables():
    """restore *persistent* iptables rules using iptables-restore

    Uses systemd's `iptables-restore` unit if it exists;
    Otherwise calls iptables-restore individualy for each rules file"""
    svc_name = "iptables-restore"
    if simple_run([str(SYSTEMCTL_PATH), "--no-pager", "cat", svc_name]):
        return simple_run([str(SYSTEMCTL_PATH), "restart", svc_name])

    return sum(
        [
            simple_run(["/sbin/iptables-restore", str(fpath)])
            for fpath in IPTABLES_DIR.glob("*.rules")
        ]
    )


def start_ap_stack():
    return sum(
        [
            restart_service("hostapd"),
            restart_service("dnsmasq"),
            restore_iptables(),
        ]
    )


def main(config_path, debug: Optional[bool] = False):
    config_path = pathlib.Path(config_path).expanduser().resolve()
    logger.info(f"Starting offspot-runtime-config off {config_path}")
    warn_unless_root()
    has_error = False

    try:
        with open(config_path, "r") as fh:
            config = from_yaml(fh.read())
    except Exception as exc:
        logger.critical(
            colored(f"Unable to read/parse YAML config at {config_path}: {exc}", "red")
        )
        start_ap_stack()
        return 1

    for key in ("timezone", "hostname", "ethernet", "ap", "containers"):
        if config.get(key):
            logger.debug(f"[{key}] config change requested")
            returncode = getattr(Handlers, f"config_{key}")(config.get(key), debug)
            if returncode == 0:
                logger.info(f"[{key}] configuration applied")
                config.pop(key)
                save_config(config_path, config)
            else:
                if returncode == 2:
                    logger.error(f"[{key}] incorrect configuration. Please fix")
                else:
                    logger.critical(f"[{key}] error applying configuration.")
                has_error = True
        elif key == "ap":
            if start_ap_stack() != 0:
                has_error = True

    if has_error:
        return 1
    succeed("runtime-config applied successfuly")


def save_config(config_path: pathlib.Path, config: Dict):
    with open(config_path, "w") as fh:
        fh.write(banner)
        fh.write(to_yaml(config) if config else "---\n")


def entrypoint():
    parser = argparse.ArgumentParser(
        prog=NAME,
        description="Configure Offspot's WiFi Access Point",
    )
    parser.add_argument("-V", "--version", action="version", version=__version__)
    parser.add_argument("--debug", action="store_true", dest="debug")

    parser.add_argument(help="Offspot Config YAML file path.", dest="config_path")

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
