import json
from typing import Optional, cast

from offspot_config.packages import AppPackage, FilesPackage, Package


class Catalog(dict):
    def __init__(self, content: Optional[str] = None):
        super().__init__()
        if content:
            self.update_from(content)

    def update_from(self, content: str):
        for entry in json.loads(content):
            cls = {"app": AppPackage, "files": FilesPackage}[entry["kind"]]
            self[entry["ident"]] = cls(**entry)

    def get_package(self, ident: str) -> Package:
        if self[ident].kind == "app":
            return cast(AppPackage, self[ident])
        elif self[ident].kind == "files":
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
