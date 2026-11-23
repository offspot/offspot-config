"""Tests for docker-compose RunningFor / State handling in get_nb_running_containers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from offspot_runtime.configlib import (
    Config,
    get_nb_running_containers,
    parse_docker_running_for,
)


@pytest.fixture(autouse=True)
def _init_logger():
    Config.init("offspot-test-running-containers")
    yield


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Less than a second", 0.0),
        ("Less than a second ago", 0.0),
        ("1 second", 1.0),
        ("12 seconds ago", 12.0),
        ("About a minute", 60.0),
        ("About a minute ago", 60.0),
        ("3 minutes", 180.0),
        ("About an hour", 3600.0),
        ("2 hours ago", 7200.0),
        ("3 weeks ago", 3 * 7 * 86400),
        ("8 months", 8 * 30 * 86400),
        ("8 months ago", 8 * 30 * 86400),
        ("2 years ago", 2 * 365 * 86400),
        ("not a duration", None),
        ("", None),
    ],
)
def test_parse_docker_running_for(text, expected):
    assert parse_docker_running_for(text) == expected
    if expected is not None and expected >= 5:
        assert parse_docker_running_for(text) >= 5


def _compose_ps(*containers: dict) -> MagicMock:
    payload = "\n".join(json.dumps(c) for c in containers) + "\n"
    completed = MagicMock()
    completed.stdout = payload
    completed.returncode = 0
    return completed


def _running(ps_result):
    with patch("offspot_runtime.configlib.subprocess.run", return_value=ps_result):
        return get_nb_running_containers()


def test_months_ago_without_healthcheck_is_counted():
    """The original crash: RunningFor '8 months ago' must not return -1."""
    assert (
        _running(
            _compose_ps(
                {
                    "Name": "hotspot",
                    "State": "running",
                    "Health": "",
                    "RunningFor": "8 months ago",
                }
            )
        )
        == 1
    )


def test_weeks_ago_still_counted():
    assert (
        _running(
            _compose_ps(
                {
                    "Name": "hotspot",
                    "State": "running",
                    "Health": "",
                    "RunningFor": "3 weeks ago",
                }
            )
        )
        == 1
    )


def test_freshly_started_container_is_not_yet_counted():
    assert (
        _running(
            _compose_ps(
                {
                    "Name": "hotspot",
                    "State": "running",
                    "Health": "",
                    "RunningFor": "2 seconds ago",
                }
            )
        )
        == 0
    )


def test_less_than_a_second_is_not_yet_counted():
    assert (
        _running(
            _compose_ps(
                {
                    "Name": "hotspot",
                    "State": "running",
                    "Health": "",
                    "RunningFor": "Less than a second ago",
                }
            )
        )
        == 0
    )


def test_healthy_container_is_counted():
    assert (
        _running(
            _compose_ps(
                {
                    "Name": "web",
                    "State": "running",
                    "Health": "healthy",
                    "RunningFor": "2 seconds ago",
                }
            )
        )
        == 1
    )


def test_exited_container_is_not_counted_even_with_old_runningfor():
    assert (
        _running(
            _compose_ps(
                {
                    "Name": "old",
                    "State": "exited",
                    "Health": "",
                    "RunningFor": "8 months ago",
                }
            )
        )
        == 0
    )


def test_unhealthy_container_is_not_promoted_by_uptime():
    assert (
        _running(
            _compose_ps(
                {
                    "Name": "sick",
                    "State": "running",
                    "Health": "unhealthy",
                    "RunningFor": "8 months ago",
                }
            )
        )
        == 0
    )


def test_started_at_timestamp_counts_when_old_enough():
    assert (
        _running(
            _compose_ps(
                {
                    "Name": "hotspot",
                    "State": "running",
                    "Health": "",
                    "StartedAt": "2020-01-01T00:00:00Z",
                }
            )
        )
        == 1
    )


def test_unparseable_running_for_does_not_fail_the_poll():
    """A single unreadable duration must not return -1 for the whole stack."""
    assert (
        _running(
            _compose_ps(
                {
                    "Name": "hotspot",
                    "State": "running",
                    "Health": "",
                    "RunningFor": "a little while",
                }
            )
        )
        == 1
    )


def test_missing_state_with_months_ago_is_counted():
    assert (
        _running(
            _compose_ps(
                {
                    "Name": "legacy",
                    "Health": "",
                    "RunningFor": "8 months ago",
                }
            )
        )
        == 1
    )


def test_compose_failure_still_returns_minus_one():
    with patch(
        "offspot_runtime.configlib.subprocess.run",
        side_effect=OSError("docker-compose missing"),
    ):
        assert get_nb_running_containers() == -1
