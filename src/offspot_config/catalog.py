from __future__ import annotations

import json
from importlib import resources
from typing import Any

import offspot_config
from offspot_config.constants import CONTENT_TARGET_PATH
from offspot_config.packages import AppPackage, FilesPackage


class AppCatalog(dict):
    def __init__(self, contents: list[dict[str, Any]] | None = None):
        super().__init__()
        if contents:
            self.update_from(contents)

    def update_from(self, contents: list[dict[str, Any]]):
        for entry in contents:
            cls = {"app": AppPackage, "files": FilesPackage}[entry["kind"]]
            self[entry["ident"]] = cls(**entry)

    def get_apppackage(self, ident: str) -> AppPackage:
        if ident not in self or not isinstance(self.get(ident, ""), AppPackage):
            raise KeyError(f"No app matching {ident}")
        return self[ident]

    def get_filespackage(self, ident: str) -> FilesPackage:
        if ident not in self or not isinstance(self.get(ident, ""), FilesPackage):
            raise KeyError(f"No files matching {ident}")
        return self[ident]


def get_app_path(package: AppPackage):
    """Dedicated on-host path for an installed App"""
    return str(CONTENT_TARGET_PATH / package.ident)


app_catalog = AppCatalog(
    json.loads((resources.files(offspot_config) / "catalog.json").read_bytes())
)
