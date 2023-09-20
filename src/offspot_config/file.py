from __future__ import annotations

import pathlib
import urllib.parse

from offspot_config.constants import DATA_PART_PATH, SUPPORTED_UNPACKING_FORMATS
from offspot_config.utils.download import get_online_rsc_size
from offspot_config.utils.misc import get_filesize


class File:
    """In-Config reference to a file to write to the data partition

    Created from files entries in config:
    - to: str
        mandatory destination to save file into. Must be inside /data
    - size: optional[int]
        size of (expanded) content. If specified, must be >= source file
    - via: optional[str]
        method to process source file (not for content). Values in File.unpack_formats
    - url: optional[str]
        URL to download file from
    - content: optional[str]
        plain text content to write to destination

    one of content or url must be supplied. content has priority"""

    kind: str = "file"  # Item interface

    unpack_formats: list[str]

    def __init__(self, payload: dict[str, str | int]):
        self.unpack_formats = ["direct", *SUPPORTED_UNPACKING_FORMATS]
        self.url: urllib.parse.ParseResult | None = None
        self.content: str = str(payload.get("content", "") or "").strip()

        if not self.content:
            try:
                self.url = urllib.parse.urlparse(str(payload["url"]))
            except Exception as exc:
                raise ValueError(f"URL “{payload.get('url')}” is incorrect") from exc

        self.to: pathlib.Path = pathlib.Path(str(payload["to"])).resolve()
        if not self.to.is_relative_to(DATA_PART_PATH):
            raise ValueError(f"{self.to} not a descendent of {DATA_PART_PATH}")

        self.via: str = str(payload.get("via", "direct"))
        if self.via not in self.unpack_formats:
            raise NotImplementedError(f"Unsupported handler `{self.via}`")

        # initialized has unknown
        self._size: int = int(payload.get("size", -1))
        self._fullsize: int | None = (
            int(payload["fullsize"]) if "fullsize" in payload else None
        )

    @property
    def source(self) -> str:  # Item interface
        return self.geturl()

    @property
    def size(self) -> int:  # Item interface
        if self._size < 0:
            return self.fetch_size()
        return self._size

    @property
    def fullsize(self):
        return self._fullsize or self.size

    def fetch_size(self, *, force: bool | None = False) -> int:
        """retrieve size of source, making sure it's reachable"""
        if not force and self._size >= 0:
            return self._size
        self._size = (
            get_filesize(self.getpath())
            if self.is_local
            else get_online_rsc_size(self.geturl())
        )
        return self._size

    def geturl(self) -> str:
        """URL as string"""
        return self.url.geturl() if self.url else ""

    def getpath(self) -> pathlib.Path:
        """URL as a local path"""
        return pathlib.Path(self.url.path if self.url else "").expanduser().resolve()

    @property
    def is_direct(self):
        return self.via == "direct"

    @property
    def is_plain(self) -> bool:
        """whether a plain text content to be written"""
        return bool(self.content)

    @property
    def is_local(self) -> bool:
        """whether referencing a local file"""
        return not self.is_plain and bool(self.url) and self.url.scheme == "file"

    @property
    def is_remote(self) -> bool:
        """whether referencing a remote file"""
        return not self.content and bool(self.url) and self.url.scheme != "file"

    def mounted_to(self, mount_point: pathlib.Path):
        """destination (to) path inside mount-point"""
        return mount_point.joinpath(self.to.relative_to(DATA_PART_PATH))

    def __repr__(self) -> str:
        msg = f"File(to={self.to}, via={self.via}"
        if self.url:
            msg += f", url={self.geturl()}"
        if self.content:
            msg += f", content={self.content.splitlines()[0][:10]}"
        msg += f", size={self.size})"
        return msg

    def __str__(self) -> str:
        return repr(self)
