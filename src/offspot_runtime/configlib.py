import datetime
import json
import logging
import os
import pathlib
import re
import subprocess
import sys
from typing import Any, NamedTuple, Optional

from attrs import define, field

from offspot_config.utils.yaml import yaml_load

SYSTEMCTL_PATH = pathlib.Path("/usr/bin/systemctl")
DNSMASQ_CONF_PATH = pathlib.Path("/etc/dnsmasq.conf")
DNSMASQ_SPOOF_CONFIG_PATH = DNSMASQ_CONF_PATH.with_name("dnsmasq-spoof.conf")
IPTABLES_DIR = pathlib.Path("/etc/iptables/")
TERM_COLORS = {"red": "31", "green": "32", "blue": "34"}
COMPOSE_PATH = pathlib.Path("/etc/docker/compose.yml")


def colored(text, color: str) -> str:
    """foreground-term-colored string"""
    value = TERM_COLORS.get(color, "39")
    return f"\033[{value}m{text}\033[39m"


logging.basicConfig(
    # level=logging.INFO, format="[\033[34m%(name)s\033[39m] %(levelname)s: %(message)s"
    level=logging.INFO,
    format=f"{colored('%(name)s', 'blue')} %(levelname)s: %(message)s",
)


class SystemDServiceStatus(NamedTuple):
    """systemctl show {service} originated info"""

    started: bool
    exit_code: int
    payload: dict[str, str]


@define
class Config:
    name: str = "-"
    debug: bool = False
    logger: logging.Logger = field(init=False)

    @classmethod
    def init(cls, name: str):
        cls.name = re.sub(r"^offspot-", "", name)
        cls.logger = logging.getLogger(name)
        cls.set_debug(enabled=cls.debug)

    @classmethod
    def set_debug(cls, *, enabled: bool = False):
        cls.debug = bool(enabled)
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


def simple_run(
    command: list[str], stdin: Optional[str] = None, *, failsafe: bool = False
):
    """returncode from running passed command, optionnaly passing str as stdin"""
    Config.logger.debug(f"{command=}")
    try:
        ps = subprocess.run(
            command,
            text=True,
            input=stdin,
            check=False,
        )
    except Exception as exc:
        if Config.debug:
            Config.logger.exception(exc)
        else:
            Config.logger.error(exc)
        return 1
    if ps.returncode != 0 and not failsafe:
        Config.logger.error(f"{ps.args} failed with returncode {ps.returncode}")
        return 1
    return ps.returncode


def get_runtime_bin(name: str) -> list[str]:
    """full path of sub-command script"""
    return get_bin(f"offspot-runtime-config-{name}")


def get_bin(name: str) -> list[str]:
    """full path of script in environment"""
    return [sys.executable, f"{sys.prefix}/bin/{name}"]


def get_progname() -> str:
    """human-friendly program name for use in usage help text"""
    try:
        return pathlib.Path(sys.argv[0]).stem
    except Exception:
        return sys.argv[0]


def ensure_folder(fpath: pathlib.Path):
    """ensures folder exists"""
    fpath.mkdir(exist_ok=True, parents=True)


def restart_service(service):
    """start or restart systemd unit based on status"""
    action = (
        "restart"
        if service_started(service).payload.get("ActiveState", "") != "running"
        else "start"
    )
    return simple_run([str(SYSTEMCTL_PATH), action, service])


def service_started(service) -> SystemDServiceStatus:
    """whether a systemd service started with details"""
    payload: dict[str, str] = {}
    command = [str(SYSTEMCTL_PATH), "--no-pager", "--plain", "show", service]
    Config.logger.debug(f"{command=}")
    try:
        ps = subprocess.run(command, text=True, capture_output=True, check=True)
        for line in ps.stdout.splitlines():
            if line.strip():
                key, value = line.split("=", 1)
                payload[key] = value
    except Exception as exc:
        if Config.debug:
            Config.logger.exception(exc)
        return SystemDServiceStatus(started=False, exit_code=99, payload={})
    else:
        succeeded = payload.get("Result", "") == "success"
        rc = int(payload.get("ExecMainStatus", "99"))
        if not succeeded:
            Config.logger.error(f"Service {service} failed with returncode {rc}")
        return SystemDServiceStatus(started=succeeded, exit_code=rc, payload=payload)


def install_dnsmasq_spoof_service(*, remove: bool):
    svcunit_path = pathlib.Path("/etc/systemd/system/toggle-dnsmasq-spoof.service")
    pathunit_path = pathlib.Path("/etc/systemd/system/toggle-dnsmasq-spoof.path")

    if remove:
        simple_run([str(SYSTEMCTL_PATH), "stop", pathunit_path.name])
        simple_run([str(SYSTEMCTL_PATH), "disable", pathunit_path.name])
        pathunit_path.unlink(missing_ok=True)
        svcunit_path.unlink(missing_ok=True)
        simple_run([str(SYSTEMCTL_PATH), "daemon-reload"])
        return 0

    svcunit_path.write_text(
        f"""[Unit]
Description=Toggle dnsmasq spoof mode based on internet connectivity

[Service]
ExecStart={" ".join(get_bin("toggle-dnsmasq-spoof"))}
"""
    )

    pathunit_path.write_text(
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



# Compose `ps --format json` reports State (running, exited, ...) and a
# human-readable RunningFor string from Docker's HumanDuration helper, often
# with an " ago" suffix. RunningFor is measured from container creation, so it
# can read "8 months ago" on a long-lived image. The generic timespan parser
# from the humanfriendly package does not accept month/year units or Docker's
# "About a minute" / "Less than a second" phrasing.


def _container_state_is_running(state: Any) -> bool:
    """True when compose/docker State looks like a running container.

    Accepts `running` (compose v2 JSON) and `Up` / `Up (healthy)` (older
    docker-compose). Missing State is treated as unknown rather than stopped.
    """
    if state is None:
        return True
    text = str(state).strip().lower()
    return text == "running" or text.startswith("up")


def parse_docker_running_for(running_for: str) -> Optional[float]:
    """Best-effort seconds from a Docker/compose RunningFor value.

    Returns None when the string cannot be parsed. Month and year use the same
    30-day / 365-day approximations as docker/go-units.HumanDuration. The
    result only needs to be compared against a small uptime threshold.
    """
    if not running_for or not isinstance(running_for, str):
        return None
    text = running_for.strip()
    text = re.sub(r"\s+ago$", "", text, flags=re.IGNORECASE).strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered == "less than a second":
        return 0.0
    if lowered == "about a minute":
        return 60.0
    if lowered == "about an hour":
        return 3600.0
    match = re.fullmatch(
        r"(\d+)\s+(second|minute|hour|day|week|month|year)s?",
        lowered,
    )
    if not match:
        return None
    count = int(match.group(1))
    unit = match.group(2)
    seconds = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
        "week": 7 * 86400,
        "month": 30 * 86400,
        "year": 365 * 86400,
    }[unit]
    return float(count * seconds)


def _parse_container_started_at(value: Any) -> Optional[datetime.datetime]:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed


def _container_uptime_seconds(container: dict[str, Any]) -> Optional[float]:
    """Uptime in seconds from a structured timestamp, else RunningFor."""
    for key in ("StartedAt", "started_at", "CreatedAt", "created_at"):
        started = _parse_container_started_at(container.get(key))
        if started is not None:
            now = datetime.datetime.now(datetime.timezone.utc)
            return max(0.0, (now - started).total_seconds())
    running_for = container.get("RunningFor")
    if running_for is None:
        running_for = container.get("running_for")
    if isinstance(running_for, str):
        return parse_docker_running_for(running_for)
    return None


def get_nb_compose_services() -> int:
    """number of expected services from reading docker-compose YAML"""
    try:
        payload = yaml_load(COMPOSE_PATH.read_text())
        if not isinstance(payload["services"], dict):
            raise ValueError("Unexpected YAML data")
        return len(payload["services"].keys())
    except Exception as exc:
        Config.logger.exception(exc)
        return 0


def get_nb_running_containers() -> int:
    """number of currently running containers (via docker-compose)"""
    containers: list[dict[str, Any]] = []
    min_seconds_healthy = 5
    try:
        ps = subprocess.run(
            [
                "/usr/local/bin/docker-compose",
                "-f",
                str(COMPOSE_PATH),
                "ps",
                "--format",
                "json",
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        for line in ps.stdout.splitlines():
            if line.strip():
                container = json.loads(line.strip())
                health = container.get("Health") or container.get("health") or ""
                state = container.get("State", container.get("state"))
                running = _container_state_is_running(state)
                if health == "healthy":
                    container["healthy"] = running
                elif not running:
                    container["healthy"] = False
                elif health and health not in ("", "starting"):
                    # Explicit non-healthy status (for example unhealthy): do
                    # not promote the container via the uptime fallback.
                    container["healthy"] = False
                else:
                    uptime = _container_uptime_seconds(container)
                    if uptime is None:
                        # State says running but no usable duration/timestamp.
                        # Do not fail the whole poll (that used to return -1
                        # and block the AP); treat as healthy.
                        container["healthy"] = True
                    else:
                        container["healthy"] = uptime >= min_seconds_healthy
                containers.append(container)
        return len(list(filter(lambda cont: cont["healthy"], containers)))
    except Exception as exc:
        Config.logger.error("failed to get compose status")
        Config.logger.exception(exc)
        return -1
