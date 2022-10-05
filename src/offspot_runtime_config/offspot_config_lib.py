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
        print("Missing YAML library (apt install python3-yaml)")
        sys.exit(1)
else:
    try:
        from yaml import CDumper as Dumper
        from yaml import CSafeLoader as SafeLoader
    except ImportError:
        from yaml import Dumper
        from yaml import SafeLoader as SafeLoader


__version__ = "1.0"
RE_IP = re.compile(
    r"^(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    r"\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    r"\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    r"\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)
SYSTEMCTL_PATH = pathlib.Path("/usr/bin/systemctl")
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


def is_valid_ip(address):
    match = RE_IP.match(address)
    if not match:
        return False
    for index, sub in enumerate(match.groups()):
        if not sub.isnumeric():
            return False
        dsub = int(sub)
        if dsub < 0 or dsub > 254:
            return False
        if index in (0, 3) and dsub == 0:
            return False
    return True


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
