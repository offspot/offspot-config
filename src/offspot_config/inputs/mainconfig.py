from __future__ import annotations

from typing import Any

from attrs import asdict, define, field
from typeguard import typechecked

from offspot_config.constants import DATA_PART_PATH
from offspot_config.file import File
from offspot_config.inputs.base import BaseConfig, get_base_from
from offspot_config.inputs.file import FileConfig
from offspot_config.inputs.oci import OCIImageConfig
from offspot_config.inputs.output import OutputConfig
from offspot_config.oci_images import OCIImage
from offspot_config.utils.misc import is_list_of_dict
from offspot_config.utils.yaml import yaml_load


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
            self.base_file = get_base_from(self.base)

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
