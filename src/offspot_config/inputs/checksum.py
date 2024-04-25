from __future__ import annotations

from attrs import asdict, define
from typeguard import typechecked

from offspot_config.constants import SUPPORTED_CHECKSUM_ALGORITHMS
from offspot_config.utils.download import read_checksum_from
from offspot_config.utils.yaml import custom_yaml_repr


@custom_yaml_repr
@typechecked
@define(kw_only=True)
class Checksum:
    """Checksum for download validation

    kind is either `digest` (default) or `url` to use the special async mode.

    In this async mode, the digest is unknown until calling `.digest` which
    resolves it by querying the URL stored in `value`.
    This allows adding files for which checksum is unknown but the web-server
    is known to provide it and is trustable (transfer validation only)"""

    algo: str
    value: str
    kind: str = "digest"

    def __attrs_post_init__(self):
        if self.algo not in SUPPORTED_CHECKSUM_ALGORITHMS:
            raise ValueError(
                f"Unsupported checksum algorith: {self.algo}. "
                f"Supported: {','.join(SUPPORTED_CHECKSUM_ALGORITHMS)}"
            )

        if self.kind not in ("digest", "url"):
            raise ValueError(
                f"Unsupported `kind`: {self.kind}. "
                "Suported: `digest` (default) or `url`"
            )

    @property
    def digest(self) -> str:
        if self.kind == "url":
            self.value = read_checksum_from(self.value)
            self.kind = "digest"
        return self.value

    @property
    def as_aria(self) -> str:
        """aria2-compatible checksum format: {algo}={digest}"""
        return f"{self.algo}={self.digest}"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @staticmethod
    def __yaml_repr__(dumper, data):
        return dumper.represent_dict(
            {key: value for key, value in asdict(data).items() if value is not None}
        )
