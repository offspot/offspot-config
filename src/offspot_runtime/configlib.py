import logging
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:
    if not os.getenv("SETUP_ONLY"):
        print(
            "Missing YAML library (apt install python3-yaml)",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)
else:
    try:
        from yaml import CDumper as Dumper
        from yaml import CSafeLoader as SafeLoader
    except ImportError:
        from yaml import Dumper
        from yaml import SafeLoader as SafeLoader


__version__ = "1.2.0"
SYSTEMCTL_PATH = pathlib.Path("/usr/bin/systemctl")
DNSMASQ_CONF_PATH = pathlib.Path("/etc/dnsmasq.conf")
DNSMASQ_SPOOF_CONFIG_PATH = DNSMASQ_CONF_PATH.with_name("dnsmasq-spoof.conf")
IPTABLES_DIR = pathlib.Path("/etc/iptables/")
TERM_COLORS = {"red": "31", "green": "32", "blue": "34"}


def colored(text, color: str) -> str:
    """foreground-term-colored string"""
    value = TERM_COLORS.get(color, "39")
    return f"\033[{value}m{text}\033[39m"


logging.basicConfig(
    # level=logging.INFO, format="[\033[34m%(name)s\033[39m] %(levelname)s: %(message)s"
    level=logging.INFO,
    format=f"{colored('%(name)s', 'blue')} %(levelname)s: %(message)s",
)


@dataclass
class Config:
    name: str = "-"
    debug: bool = False
    logger = None

    @classmethod
    def init(cls, name: str):
        cls.name = re.sub(r"^offspot-", "", name)
        cls.logger = logging.getLogger(name)
        cls.set_debug(cls.debug)

    @classmethod
    def set_debug(cls, enabled: bool = False):
        cls.debug = enabled
        if enabled:
            cls.logger.setLevel(logging.DEBUG)


def fail_invalid(message: str):
    Config.logger.error(colored(message, "red"))
    sys.exit(2)


def fail_error(message: str):
    Config.logger.critical(colored(message, "red"))
    sys.exit(1)


def succeed(message: str) -> int:
    Config.logger.info(colored(message, "green"))
    return 0


def warn_unless_root():
    if os.getuid() != 0:
        Config.logger.warning(f"you are not root! uid={os.getuid()}")


def simple_run(command: List[str], stdin: Optional[str] = None):
    """returncode from running passed command, optionnaly passing str as stdin"""
    Config.logger.debug(f"{command=}")
    try:
        ps = subprocess.run(
            command,
            text=True,
            input=stdin,
        )
    except Exception as exc:
        if Config.debug:
            Config.logger.exception(exc)
        else:
            Config.logger.error(exc)
        return 1
    if ps.returncode != 0:
        Config.logger.error(f"{ps.args} failed with returncode {ps.returncode}")
        return 1
    return ps.returncode


def get_bin(name: str) -> str:
    """full path of sub-command script"""
    return ["/usr/bin/env", f"offspot-config-{name}"]


def get_progname() -> str:
    """human-friendly program name for use in usage help text"""
    try:
        return pathlib.Path(sys.argv[0]).stem
    except Exception:
        return sys.argv[0]


def ensure_folder(fpath: pathlib.Path):
    """ensures folder exists"""
    fpath.mkdir(exist_ok=True, parents=True)


def to_yaml(payload: Dict) -> str:
    """serialize object into a YAML string"""
    return yaml.dump(payload, Dumper=Dumper)


def from_yaml(payload: str) -> Dict:
    """serialize object into a YAML string"""
    return yaml.load(payload, Loader=SafeLoader) or {}


def restart_service(service):
    """start or restart systemd unit based on status"""
    action = (
        "restart"
        if simple_run([str(SYSTEMCTL_PATH), "--no-pager", "status", service]) == 0
        else "start"
    )
    return simple_run([str(SYSTEMCTL_PATH), action, service])


def install_dnsmasq_spoof_service(remove: Optional[bool] = False):
    svcunit_path = pathlib.Path("/etc/systemd/system/toggle-dnsmasq-spoof.service")
    pathunit_path = pathlib.Path("/etc/systemd/system/toggle-dnsmasq-spoof.path")

    if remove:
        simple_run([str(SYSTEMCTL_PATH), "stop", pathunit_path.name]),
        simple_run([str(SYSTEMCTL_PATH), "disable", pathunit_path.name]),
        pathunit_path.unlink(missing_ok=True)
        svcunit_path.unlink(missing_ok=True)
        simple_run([str(SYSTEMCTL_PATH), "daemon-reload"])
        return 0

    with open(svcunit_path, "w") as fh:
        fh.write(
            """[Unit]
Description=Toggle dnsmasq spoof mode based on internet connectivity

[Service]
ExecStart=toggle-dnsmasq-spoof
"""
        )

    with open(pathunit_path, "w") as fh:
        fh.write(
            """[Unit]
Description="Monitor internet connectivity file for changes"

[Path]
PathModified=/var/run/internet
Unit=toggle-dnsmasq-spoof.service

[Install]
WantedBy=multi-user.target
"""
        )
    return sum(
        [
            simple_run([str(SYSTEMCTL_PATH), "daemon-reload"]),
            simple_run([str(SYSTEMCTL_PATH), "enable", pathunit_path.name]),
            simple_run([str(SYSTEMCTL_PATH), "start", pathunit_path.name]),
        ]
    )
