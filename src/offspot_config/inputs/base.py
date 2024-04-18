from __future__ import annotations

import re

from attrs import define
from typeguard import typechecked

from offspot_config.constants import DATA_PART_PATH
from offspot_config.file import File
from offspot_config.inputs.checksum import Checksum
from offspot_config.utils.download import read_checksum_from
from offspot_config.utils.misc import parse_size


def get_base_from(base: BaseConfig) -> File:
    """Infer url from flexible `base` and return a File"""
    payload: dict[str, str | int | dict[str, str]] = {
        "url": str(base.source),
        "to": str(DATA_PART_PATH / "-"),
    }
    match = re.match(
        r"^(?P<version>\d\.\d\.\d)(?P<extra>[a-z0-9\-\.\_]*)", str(base.source)
    )
    if match:
        version = "".join(match.groups())
        payload["url"] = (
            f"https://drive.offspot.it/base/offspot-base-arm64-{version}.img"
        )
        try:
            payload["checksum"] = Checksum(
                algo="md5", value=read_checksum_from(f"{payload['url']}.md5")
            ).to_dict()
        except Exception:
            ...
    elif isinstance(base.checksum, Checksum):
        payload["checksum"] = base.checksum.to_dict()
    return File(payload)


@typechecked
@define(kw_only=True)
class BaseConfig:
    source: str | File
    rootfs_size: str | int
    checksum: dict[str, str] | Checksum | None = None

    def __attrs_post_init__(self):
        if self.rootfs_size and isinstance(self.rootfs_size, str):
            self.rootfs_size = parse_size(self.rootfs_size)
        if self.checksum and isinstance(self.checksum, dict):
            self.checksum = Checksum(**self.checksum)
