from __future__ import annotations

import pathlib
import urllib.parse
from typing import NamedTuple, TypeVar

from offspot_config.inputs.checksum import Checksum
from offspot_config.utils.download import get_online_rsc_size

R = TypeVar("R", bound="Reader")


class Reader(NamedTuple):
    """Downloadable Kiwix Reader software information

    Used to build offspot dashboard so it can offer links to download said softwares
    allowing users to use ZIMs locally"""

    platform: str
    download_url: str
    filename: str
    size: int
    checksum: Checksum | None = None

    def to_dict(self) -> dict[str, str | int]:
        def value_or_dict(value):
            if hasattr(value, "to_dict"):
                return value.to_dict()
            return value

        return {field: value_or_dict(getattr(self, field)) for field in self._fields}

    def to_dashboard_dict(self, download_fqdn: str) -> dict[str, str | int]:
        data = self.to_dict()
        data["download_url"] = f"//{download_fqdn}/{data['filename']!s}"
        return data

    @property
    def order(self) -> int:
        """sort-usable order based on reader's platform popularity"""
        return {"windows": 0, "android": 1, "macos": 2, "linux": 3}.get(
            self.platform, 4
        )

    @classmethod
    def using(
        cls: type[R], platform: str, download_url: str, checksum: Checksum | None = None
    ) -> R:
        """Reader from a platform name and download URL"""
        return cls(
            platform=platform,
            download_url=download_url,
            size=get_online_rsc_size(download_url),
            filename=cls.filename_from_url(download_url),
            checksum=checksum,
        )

    @staticmethod
    def filename_from_url(url: str) -> str:
        """suggested filename from reader download URL"""
        return pathlib.Path(urllib.parse.urlparse(url).path).name

    @staticmethod
    def sort(reader: Reader) -> int:
        """sorted key function to sort by reader's order"""
        return reader.order


class Link(NamedTuple):
    """Link to an arbitrary resource

    used to build offspot dashboard so additional (not content) resources can be
    linked to

    icon is tied to implementation and currently should be either unset (empty)
    or the name of a FontAwesome 6 icon
    https://fontawesome.com/v6/search?o=r&m=free"""

    label: str
    url: str
    icon: str = ""

    def to_dict(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in self._fields}
