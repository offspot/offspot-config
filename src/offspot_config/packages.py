from __future__ import annotations

import re
import uuid

from attrs import define, field
from pathvalidate import sanitize_filename
from typeguard import typechecked

from offspot_config.constants import CONTENT_TARGET_PATH
from offspot_config.inputs.checksum import Checksum
from offspot_config.inputs.file import FileConfig
from offspot_config.oci_images import OCIImage
from offspot_config.utils.download import get_base64_from


@typechecked
@define(kw_only=True)
class Package:
    ident: str
    kind: str
    domain: str
    title: str
    description: str
    tags: list[str] = field(kw_only=True, factory=list)
    languages: list[str] | None = None
    icon_url: str | None = None

    @property
    def size(self) -> int:
        raise NotImplementedError()

    def get_url(self, fqdn: str, **kwargs) -> str:  # noqa: ARG002
        return ""

    def get_download_url(self, download_fqdn: str) -> str | None:  # noqa: ARG002
        return None

    def get_download_size(self) -> int | None:
        return None

    def get_download_checksum(self) -> Checksum | None:
        return None

    def to_dashboard_entry(
        self, fqdn: str, kiwix_domain: str, download_fqdn: str | None
    ):
        entry = {
            "ident": self.ident,
            "kind": self.kind,
            "title": self.title,
            "description": self.description,
            "languages": self.languages,
            "tags": self.tags,
            "url": self.get_url(fqdn, kiwix_domain=kiwix_domain),
            "icon": get_base64_from(self.icon_url) if self.icon_url else "",
        }
        if self.get_download_url(str(download_fqdn)) and self.get_download_size():
            download = {
                "download": {
                    "url": self.get_download_url(str(download_fqdn)),
                    "size": self.get_download_size(),
                }
            }
            if self.get_download_checksum():
                download["download"]["checksum"] = self.get_download_checksum()
            entry.update(download)
        return entry


@typechecked
@define(kw_only=True)
class ZimPackage(Package):
    kind: str = "zim"
    domain: str = "kiwix"
    download_checksum: Checksum | None = None

    ident: str
    name: str
    flavour: str
    version: str

    download_url: str
    download_size: int

    @property
    def url_path(self):
        return self.name

    @property
    def filename(self):
        from offspot_config.zim import from_ident

        info = from_ident(self.ident)
        fname = sanitize_filename(f"{info.publisher}_{info.name}_{info.flavour}")
        return f"{fname}.zim"

    @property
    def size(self) -> int:
        return self.download_size

    def get_url(self, fqdn: str, kiwix_domain: str, **kwargs) -> str:  # noqa: ARG002
        # this assumes that the ZIM is stored using self.filename
        from offspot_config.zim import get_libkiwix_humanid

        return f"//{kiwix_domain}.{fqdn}/viewer#{get_libkiwix_humanid(self.filename)}"

    def get_download_url(self, download_fqdn: str) -> str:
        return f"//{download_fqdn}/{self.filename}"

    def get_download_size(self) -> int:
        return self.download_size

    def get_download_checksum(self) -> Checksum | None:
        return self.download_checksum


@typechecked
@define(kw_only=True)
class AppPackage(Package):
    ident: str
    image: str
    image_filesize: int
    image_fullsize: int
    download_url: str | None = None
    download_size: int | None = None
    download_checksum: Checksum | None = None
    download_to: str | None = None
    download_via: str | None = "direct"
    # map of global:local environ to pass from config to container
    environ_map: dict[str, str] | None = None
    # custom static/dynamic environ for app
    environ: dict[str, str] | None = None
    # list of volumes to mount in host:container[:ro] format
    volumes: list[str] | None = None
    # list of links to services to add to hosts in service[:alias] format
    links: list[str] | None = None
    # map of subdomain to target (service-name:port) to add to reverse proxy
    sub_services: dict[str, str] | None = None
    # username, password to password-protect the service with
    protected_by: tuple[str, str] | None = None

    @property
    def oci_image(self):
        return OCIImage(
            ident=self.image, filesize=self.image_filesize, fullsize=self.image_fullsize
        )

    @property
    def filename(self):
        return self.download_to if self.download_to else self.ident

    @property
    def app_id(self):
        ident = self.ident.strip()
        return (
            re.sub(r"[^a-zA-Z0-9]", "", ident[0])
            + re.sub(r"[^a-zA-Z0-9_.-]+", "", ident[1:])
        ) or uuid.uuid4().hex

    @property
    def size(self) -> int:
        return self.image_fullsize + (self.download_size or 0)

    def get_url(self, fqdn: str, **kwargs) -> str:  # noqa: ARG002
        return f"//{self.domain}.{fqdn}/"

    def has_file(self) -> bool:
        return bool(self.download_url)

    def as_fileconfig(self) -> FileConfig | None:
        if not self.has_file:
            return None
        return FileConfig(
            to=str(CONTENT_TARGET_PATH / self.filename),
            url=self.download_url,
            via=self.download_via,
            size=self.download_size,
            checksum=self.download_checksum,
        )

    def get_download_size(self) -> int:
        return self.download_size or 0

    def get_download_checksum(self) -> Checksum | None:
        return self.download_checksum


@typechecked
@define(kw_only=True)
class FilesPackage(Package):
    ident: str
    via: str
    download_url: str
    download_size: int | None = None
    download_checksum: Checksum | None = None
    target: str | None = None

    @property
    def filename(self):
        return self.target if self.target else self.ident

    @property
    def size(self) -> int:
        return self.download_size or 0

    def get_url(self, fqdn: str, **kwargs) -> str:  # noqa: ARG002
        return f"//{self.domain}.{fqdn}/"

    def as_fileconfig(self) -> FileConfig:
        return FileConfig(
            to=str(CONTENT_TARGET_PATH / "files" / self.filename),
            url=self.download_url,
            content=None,
            via=self.via,
            size=self.download_size,
            checksum=self.download_checksum,
        )

    def get_download_size(self) -> int:
        return self.size

    def get_download_checksum(self) -> Checksum | None:
        return self.download_checksum
