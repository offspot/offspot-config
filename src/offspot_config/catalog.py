from __future__ import annotations

import json
from importlib import resources
from typing import Any, cast

import offspot_config
from offspot_config.constants import CONTENT_TARGET_PATH
from offspot_config.packages import AppPackage, FilesPackage, Package


class AppCatalog(dict):
    def __init__(self, contents: list[dict[str, Any]] | None = None):
        super().__init__()
        if contents:
            self.update_from(contents)

    def update_from(self, contents: list[dict[str, Any]]):
        for entry in contents:
            cls = {"app": AppPackage, "files": FilesPackage}[entry["kind"]]
            self[entry["ident"]] = cls(**entry)

    def get_package(self, ident: str) -> Package:
        if self[ident]["kind"] == "app":
            return cast(AppPackage, self[ident])
        elif self[ident]["kind"] == "files":
            return cast(FilesPackage, self[ident])
        return self[ident]

    def get_apppackage(self, ident: str) -> AppPackage:
        package = self.get_package(ident)
        if not isinstance(package, AppPackage):
            raise KeyError("No app matching {ident}")
        return package

    def get_filespackage(self, ident: str) -> FilesPackage:
        package = self.get_package(ident)
        if not isinstance(package, FilesPackage):
            raise KeyError("No files matching {ident}")
        return package


def get_app_path(package: AppPackage):
    """Dedicated on-host path for an installed App"""
    return str(CONTENT_TARGET_PATH / package.ident)


app_catalog = AppCatalog(
    json.loads((resources.files(offspot_config) / "catalog.json").read_bytes())
)
