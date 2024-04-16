from __future__ import annotations

from attrs import define
from typeguard import typechecked


@typechecked
@define(kw_only=True)
class OCIImageConfig:
    ident: str
    url: str | None = None
    filesize: int
    fullsize: int
