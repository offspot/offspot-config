from __future__ import annotations

import re
import uuid

from attrs import define, field
from typeguard import typechecked

from offspot_config.constants import CONTENT_TARGET_PATH
from offspot_config.inputs import FileConfig
from offspot_config.oci_images import OCIImage

# @typechecked
# @define(kw_only=True)
# class BaseImage:
#     source: str
#     root_size: int


@typechecked
@define(kw_only=True)
class Package:
    kind: str
    domain: str
    title: str
    description: str
    tags: list[str] = field(kw_only=True, factory=list)
    languages: list[str] | None = None
    icon: str | None = None

    def get_url(self, fqdn: str, **kwargs) -> str:  # noqa: ARG002
        return ""

    def get_download_url(self, download_fqdn: str) -> str | None:  # noqa: ARG002
        return None

    def get_download_size(self) -> int | None:
        return None

    def to_dashboard_entry(self, fqdn: str, download_fqdn: str | None):
        entry = {
            "kind": self.kind,
            "title": self.title,
            "description": self.description,
            "languages": self.languages,
            "tags": self.tags,
            "url": self.get_url(fqdn),
        }
        if self.get_download_url(str(download_fqdn)) and self.get_download_size():
            entry.update(
                {
                    "download": {
                        "url": self.get_download_url(str(download_fqdn)),
                        "size": self.get_download_size(),
                    }
                }
            )
        return entry


@typechecked
@define(kw_only=True)
class ZimPackage(Package):
    kind: str = "zim"
    domain: str = "kiwix"

    ident: str
    name: str
    flavour: str
    version: str

    download_url: str
    download_size: int

    @property
    def url_path(self):
        return self.ident.split(":", 2)[1]

    @property
    def filename(self):
        return f"{self.url_path}.zim"

    def get_url(
        self, fqdn: str, kiwix_domain: str | None = "kiwix", **kwargs  # noqa: ARG002
    ) -> str:
        return f"//{kiwix_domain}.{fqdn}/viewer#{self.url_path}"

    def get_download_url(self, download_fqdn: str) -> str:
        return f"//{download_fqdn}/{self.filename}"

    def get_download_size(self) -> int:
        return self.download_size


@typechecked
@define(kw_only=True)
class AppPackage(Package):
    ident: str
    image: str
    image_filesize: int
    image_fullsize: int
    download_url: str | None = None
    download_size: int | None = None
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

    def get_url(self, fqdn: str, **kwargs) -> str:  # noqa: ARG002
        return f"//{self.domain}.{fqdn}/{self.ident}"

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
        )


@typechecked
@define(kw_only=True)
class FilesPackage(Package):
    ident: str
    via: str
    download_url: str
    download_size: int | None = None
    target: str | None = None

    @property
    def filename(self):
        return self.target if self.target else self.ident

    def get_url(self, fqdn: str, **kwargs) -> str:  # noqa: ARG002
        return f"//{self.domain}.{fqdn}/"

    def as_fileconfig(self) -> FileConfig:
        return FileConfig(
            to=str(CONTENT_TARGET_PATH / "files" / self.filename),
            url=self.download_url,
            content=None,
            via=self.via,
            size=self.download_size,
        )
