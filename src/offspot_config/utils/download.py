from __future__ import annotations

import base64

import requests
import requests.adapters
from urllib3.util.retry import Retry

session = requests.Session()
# basic urllib retry mechanism.
# Sleep (seconds): {backoff factor} * (2 ** ({number of total retries} - 1))
# https://docs.descarteslabs.com/_modules/urllib3/util/retry.html
retries = Retry(
    total=10,  # Total number of retries to allow. Takes precedence over other counts.
    connect=5,  # How many connection-related errors to retry on
    read=5,  # How many times to retry on read errors
    redirect=20,  # How many redirects to perform. (to avoid infinite redirect loops)
    status=3,  # How many times to retry on bad status codes
    other=0,  # How many times to retry on other errors
    allowed_methods=None,  # Set of HTTP verbs that we should retry on (False is all)
    status_forcelist=[
        413,
        429,
        500,
        502,
        503,
        504,
    ],  # Set of integer HTTP status we should force a retry on
    backoff_factor=30,  # backoff factor to apply between attempts after the second try,
    backoff_max=1800.0,  # allow up-to 30mn backoff (default 2mn)
    raise_on_redirect=False,  # raise MaxRetryError instead of 3xx response
    raise_on_status=False,  # raise on Bad Status or response
    respect_retry_after_header=True,  # respect Retry-After header (status_forcelist)
)
session.mount("http", requests.adapters.HTTPAdapter(max_retries=retries))


def get_online_rsc_size(url: str) -> int:
    """size (Content-Length) from url if specified, -1 otherwise (-2 on errors)"""
    try:
        resp = session.head(url, allow_redirects=True, timeout=60)
        # some servers dont offer HEAD
        if resp.status_code != 200:
            resp = requests.get(
                url,
                allow_redirects=True,
                timeout=60,
                stream=True,
                headers={"Accept-Encoding": "identity"},
            )
            resp.raise_for_status()
        return int(resp.headers.get("Content-Length") or -1)
    except Exception:
        return -2


def get_base64_from(url: str) -> str:
    try:
        return base64.b64encode(session.get(url).content).decode("ASCII")
    except Exception:
        return ""
