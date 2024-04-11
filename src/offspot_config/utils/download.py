from __future__ import annotations

import base64
import io

import requests
import requests.adapters
from urllib3.util.retry import Retry

from offspot_config.constants import MAX_DIRECT_ONLINE_RESOURCE_PAYLOAD_SIZE

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
        return base64.b64encode(get_payload_from(url)).decode("ASCII")
    except Exception:
        return ""


def get_payload_from(
    url: str, no_more_than: int = MAX_DIRECT_ONLINE_RESOURCE_PAYLOAD_SIZE
) -> bytes:
    """Retrieved content from an URL

    Limited in order to prevent download bomb.

    Parameters:
        url: URL to retrieve payload from (follows redirects)
        no_more_than: number of bytes to consider too much and fail at

    Raises:
        OSError: Should declared or retrieved size exceed no_more_than
        RequestException: HTTP or other error in requests
        ConnectionError: connection issues
        Timeout: ReadTimeout or request timeout"""
    size = get_online_rsc_size(url)
    if no_more_than and size > no_more_than:
        raise OSError(f"URL content is larger than {no_more_than!s}")

    resp = session.get(url, stream=True, allow_redirects=True, timeout=60)
    resp.raise_for_status()
    downloaded = 0
    payload = io.BytesIO()
    for data in resp.iter_content(2**30):
        downloaded += len(data)
        if no_more_than and downloaded > no_more_than:
            raise OSError(f"URL content is larger than {no_more_than!s}")
        payload.write(data)
    payload.seek(0)
    return payload.getvalue()


def read_checksum_from(url: str) -> str:
    """checksum from mirrorbrain-like (or raw) digest URL

        Format can be the raw digest or digest and filename:
            9e92449ce93115e8d85e29e8e584dece  wikipedia_ab_all_maxi_2024-02.zim

    Parameters:
        url: URL to read from. eg: download.kiwix.org/x/y/z.zim.sha1

    Raises:
        OSError: Should declared or retrieved size exceed no_more_than
        RequestException: HTTP or other error in requests
        ConnectionError: connection issues
        Timeout: ReadTimeout or request timeout
        UnicodeDecodeError: content cannot be decoded into ASCII
        UnicodeEncodeError: content  cannot be encoded into UTF-8
        IndexError: content is empty or malformed
    """
    return (
        get_payload_from(url, no_more_than=2 * 2**10)
        .decode("UTF-8")
        .strip()
        .split(maxsplit=1)[0]
        .encode("UTF-8")
        .decode("ASCII")
    )
