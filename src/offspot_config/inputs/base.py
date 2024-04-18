from __future__ import annotations

import re

from attrs import define
from typeguard import typechecked

from offspot_config.constants import DATA_PART_PATH
from offspot_config.file import File
from offspot_config.utils.misc import parse_size


def get_base_from(url: str) -> File:
    """Infer url from flexible `base` and return a File"""
    match = re.match(r"^(?P<version>\d\.\d\.\d)(?P<extra>[a-z0-9\-\.\_]*)", url)
    if match:
        version = "".join(match.groups())
        url = f"https://drive.offspot.it/base/offspot-base-arm64-{version}.img"
    return File({"url": url, "to": str(DATA_PART_PATH / "-")})


@typechecked
@define(kw_only=True)
class BaseConfig:
    source: str | File
    rootfs_size: str | int

    def __attrs_post_init__(self):
        if self.rootfs_size and isinstance(self.rootfs_size, str):
            self.rootfs_size = parse_size(self.rootfs_size)
