from __future__ import annotations

from attrs import asdict, define
from typeguard import typechecked

from offspot_config.file import File
from offspot_config.inputs.checksum import Checksum
from offspot_config.inputs.str import BlockStr
from offspot_config.inputs.ways import WAYS
from offspot_config.utils.misc import parse_size
from offspot_config.utils.yaml import custom_yaml_repr


@custom_yaml_repr
@typechecked
@define(kw_only=True)
class FileConfig:
    to: str
    url: str | None = None
    content: BlockStr | None = None
    via: str | None = "direct"
    size: str | int | None = -1
    checksum: Checksum | None = None

    def __attrs_post_init__(self):
        if self.via not in WAYS:
            raise ValueError(
                f"Incorrect value `{self.via}` for {type(self).__name__}.via"
            )
        if not self.url and not self.content:
            raise ValueError(
                f"Either {type(self).__name__}.url "
                f"or {type(self).__name__}.content must be set"
            )
        if self.size and isinstance(self.size, str):
            self.size = parse_size(self.size)

        if self.content and not isinstance(self.content, BlockStr):
            self.content = BlockStr(self.content)

    @property
    def file(self) -> File:
        return File(asdict(self))

    @staticmethod
    def __yaml_repr__(dumper, data):
        return dumper.represent_dict(
            {key: value for key, value in asdict(data).items() if value is not None}
        )
