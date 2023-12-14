from __future__ import annotations

import re
from typing import Any

from attrs import asdict, define, field
from typeguard import typechecked

from offspot_config.constants import DATA_PART_PATH
from offspot_config.file import File
from offspot_config.oci_images import OCIImage
from offspot_config.utils.misc import is_list_of_dict, parse_size
from offspot_config.utils.yaml import custom_yaml_repr, yaml_load

WAYS = ("direct", "bztar", "gztar", "tar", "xztar", "zip")


def get_base_from(url: str) -> File:
    """Infer url from flexible `base` and return a File"""
    match = re.match(r"^(?P<version>\d\.\d\.\d)(?P<extra>[a-z0-9\-\.\_]*)", url)
    if match:
        version = "".join(match.groups())
        url = f"https://drive.offspot.it/base/offspot-base-arm64-{version}.img.xz"
    return File({"url": url, "to": str(DATA_PART_PATH / "-")})


@custom_yaml_repr
class BlockStr(str):
    """A string containing a large amount of text, usually representing a file"""

    @staticmethod
    def __yaml_repr__(dumper, data):
        """represent BlockStr as multiline"""
        return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style="|")


@typechecked
@define(kw_only=True)
class BaseConfig:
    source: str | File
    rootfs_size: str | int

    def __attrs_post_init__(self):
        if self.rootfs_size and isinstance(self.rootfs_size, str):
            self.rootfs_size = parse_size(self.rootfs_size)


@typechecked
@define(kw_only=True)
class OCIImageConfig:
    ident: str
    url: str | None = None
    filesize: int
    fullsize: int


@custom_yaml_repr
@typechecked
@define(kw_only=True)
class FileConfig:
    to: str
    url: str | None = None
    content: BlockStr | None = None
    via: str | None = "direct"
    size: str | int | None = -1

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


@typechecked
@define(kw_only=True)
class MainConfig:
    base: dict | BaseConfig
    base_file: File | None = None
    output: dict | OutputConfig | None = field(factory=OutputConfig)
    oci_images: list[OCIImageConfig]
    files: list[FileConfig]
    write_config: bool | None = False
    offspot: dict[str, Any] | None = field(factory=dict)

    all_files: list[File] = field(factory=list)
    all_images: list[OCIImage] = field(factory=list)

    def __attrs_post_init__(self):
        if isinstance(self.base, dict):
            self.base = BaseConfig(**self.base)

        if isinstance(self.base.source, str):
            self.base_file = get_base_from(self.base.source)

        if isinstance(self.output, dict):
            self.output = OutputConfig(**self.output)

        all_tos = [fileconf.to for fileconf in self.files]
        dup_tos = [to for to in all_tos if all_tos.count(to) > 1]
        if len(dup_tos):
            raise ValueError(
                f"{type(self).__name__}.files: duplicate to target(s): "
                f"{','.join(dup_tos)}"
            )

        for conf in self.files:
            self.all_files.append(File(asdict(conf)))
        for conf in self.oci_images:
            self.all_images.append(OCIImage(**asdict(conf)))

    @property
    def rootfs_size(self) -> int:
        if not isinstance(self.base, BaseConfig) or not isinstance(
            self.base.rootfs_size, int
        ):
            raise OSError("Base not ready")
        return self.base.rootfs_size

    @classmethod
    def read_from(cls, text: str):
        """Config from a YAML string config"""

        # parse YAML (Dict) will be our input to MainConfig
        payload = yaml_load(text)

        # handle write_config request:
        # add raw config content to image.yaml on disk (before config parsing)
        if payload.get("write_config"):
            payload["files"].append(
                {
                    "to": str(DATA_PART_PATH / "image.yaml"),
                    "content": text,
                    "via": "direct",
                    "size": len(text.encode("utf-8")),
                }
            )

        # build SubPolicies first (args of the main Policy)
        for name, sub_config_cls in {
            "oci_images": OCIImageConfig,
            "files": FileConfig,
        }.items():
            # remove he key from payload ; we'll replace it with actual SubConfig
            subload = payload.pop(name, [])

            if not is_list_of_dict(subload):
                raise ValueError(f"Unexpected type for Config.{name}: {type(subload)}")

            # create SubConfig (will fail in case of errors)
            payload[name] = [sub_config_cls(**item) for item in subload]

        # ready to create the actual main Policy
        return cls(**payload)

    @property
    def remote_files(self) -> list[File]:
        return [file for file in self.all_files if file.is_remote]

    @property
    def non_remote_files(self) -> list[File]:
        return [file for file in self.all_files if file.is_plain or file.is_local]
