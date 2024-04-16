from __future__ import annotations

from attrs import define
from typeguard import typechecked

from offspot_config.utils.misc import parse_size


@typechecked
@define(kw_only=True)
class OutputConfig:
    size: int | str | None = None
    compress: bool | None = False

    def __attrs_post_init__(self):
        self.parse_size()

    def parse_size(self):
        if isinstance(self.size, int):
            return

        if self.size == "auto":
            self.size = None
            return
        try:
            self.size = parse_size(str(self.size))
        except Exception as exc:
            raise ValueError(
                f"Unable to parse `{self.size}` into size "
                f"for {type(self).__name__}.size ({exc})"
            ) from exc
