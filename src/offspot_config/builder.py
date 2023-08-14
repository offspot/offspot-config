from __future__ import annotations

from typing import Any

from offspot_config.constants import CONTENT_TARGET_PATH
from offspot_config.inputs import BaseConfig, BlockStr, FileConfig
from offspot_config.oci_images import OCIImage
from offspot_config.packages import AppPackage, FilesPackage, ZimPackage
from offspot_config.utils.yaml import yaml_dump


class ConfigBuilder:
    def __init__(
        self,
        *,
        base: BaseConfig,
        name: str = "My Offspot",
        tld: str | None = "offspot",
        domain: str | None = "my-offspot",
        ssid: str | None = "my-offspot",
        passphrase: str | None = None,
        timezone: str | None = "UTC",  # noqa: ARG002
        as_gateway: bool | None = False,
        write_config: bool | None = False,
    ):
        self.name = name
        self.config: dict[str, Any] = {
            "base": {"source": base.source, "rootfs_size": base.rootfs_size},
            "output": {"size": "auto"},
            "oci_images": set(),
            "files": [],
            "write_config": write_config,
            "offspot": {
                "containers": {"name": "offspot", "services": {}},
                "ap": {
                    "domain": domain,
                    "tld": tld,
                    "ssid": ssid,
                    "passphrase": passphrase,
                    "as-gateway": as_gateway,
                },
                "ethernet": {"type": "dhcp"},
                "timezone": "UTC",
            },
        }

        # whether dashboard will offer downloads for ZIM files
        self.dashboard_offers_zim_downloads = True
        # every card the dashboard will display
        self.dashboard_entries = []
        # all files that will be downloaded and places onto disk
        self.file_entries = []
        # domain of services that must be reversed to (all but special cases)
        self.reversed_services = set()
        # domain: folder map of virtual services serving only files
        self.files_mapping = {}

        self.with_kiwixserve: bool = False
        self.with_files: bool = False
        self.with_reverseproxy: bool = False
        self.with_dashboard: bool = False
        self.with_captive_portal: bool = False
        self.with_hwclock: bool = False

    @property
    def compose(self):
        return self.config["offspot"]["containers"]

    @property
    def fqdn(self):
        return (
            f"{self.config['offspot']['ap']['domain']}."
            f"{self.config['offspot']['ap']['tld']}"
        )

    def update_offspot_config(self, **kwargs):
        self.config["offspot"].update(kwargs)

    # def add_package(self, ident: str):
    #     try:
    #         prefix, ident = ident.split(":", 1)
    #     except Exception as exc:
    #         raise ValueError(
    #             f"Invalid prefix:ident value for package: {ident}"
    #         ) from exc

    #     if prefix == "zim":
    #         return self.add_zim(ident)
    #     if prefix == "app":
    #         return self.add_app(ident)
    #     if prefix == "file":
    #         return self.add_files_package(ident)

    #     raise ValueError(f"Invalid package prefix: {prefix}")

    def set_output_size(self, size: int):
        self.config["output"]["size"] = size

    def add_dashboard(self, *, allow_zim_downloads: bool | None = False):
        self.dashboard_offers_zim_downloads = allow_zim_downloads
        if self.with_dashboard:
            return

        self.with_dashboard = True

        image = OCIImage(
            ident="ghcr.io/offspot/dashboard:1.0",
            filesize=119941120,
            fullsize=119838811,
        )
        self.config["oci_images"].add(image)

        # add to compose
        self.compose["services"]["home"] = {
            "image": image.source,
            "container_name": "home",
            "pull_policy": "never",
            "restart": "unless-stopped",
            "expose": ["80"],
            "volumes": [
                {
                    "type": "bind",
                    "source": str(CONTENT_TARGET_PATH / "dashboard.yaml"),
                    "target": "/src/home.yaml",
                    "read_only": True,
                }
            ],
        }

    def gen_dashboard_config(self):
        """Generate and add YAML config file for dashboard, based on entries"""

        if self.dashboard_offers_zim_downloads:
            download_fqdn = f"download-zims.{self.fqdn}"
        else:
            download_fqdn = None

        payload = {
            "metadata": {"name": self.name, "fqdn": self.fqdn},
            "packages": [
                package.to_dashboard_entry(fqdn=self.fqdn, download_fqdn=download_fqdn)
                for package in self.dashboard_entries
            ],
        }

        self.add_file(
            url_or_content=BlockStr(yaml_dump(payload)),
            to=str(CONTENT_TARGET_PATH / "dashboard.yaml"),
            size=0,
            via="direct",
            is_url=False,
        )

    def add_reverseproxy(self):
        if self.with_reverseproxy:
            return

        self.with_reverseproxy = True

        image = OCIImage(
            ident="ghcr.io/offspot/reverse-proxy:1.0",
            filesize=114974720,
            fullsize=114894424,
        )
        self.config["oci_images"].add(image)

        # add to compose
        self.compose["services"]["reverse-proxy"] = {
            "image": image.source,
            "container_name": "reverse-proxy",
            "environment": {
                "FQDN": self.fqdn,
            },
            "pull_policy": "never",
            "restart": "unless-stopped",
            "ports": ["80:80", "443:443"],
        }

    def add_captive_portal(self):
        if self.with_captive_portal:
            return

        self.with_captive_portal = True

        image = OCIImage(
            ident="ghcr.io/offspot/captive-portal:1.0",
            filesize=187668480,
            fullsize=187604243,
        )
        self.config["oci_images"].add(image)

        # add to compose
        self.compose["services"]["home-portal"] = {
            "image": image.source,
            "container_name": "home-portal",
            "network_mode": "host",
            "cap_add": [
                "NET_ADMIN",
            ],
            "environment": {
                "HOTSPOT_NAME": self.name,
                "HOTSPOT_IP": "192.168.2.1",
                "HOTSPOT_FQDN": self.fqdn,
                "CAPTURED_NETWORKS": "192.168.2.128/25",
                "TIMEOUT": "60",
                "FILTER_MODULE": "portal_filter",
            },
            "pull_policy": "never",
            "restart": "unless-stopped",
            "expose": ["2080", "2443"],
            "volumes": [
                {
                    "type": "bind",
                    "source": "/var/run/internet",
                    "target": "/var/run/internet",
                    "read_only": True,
                }
            ],
        }

    def add_hwclock(self):
        if self.with_hwclock:
            return

        self.with_hwclock = True

        # add image
        image = OCIImage(
            ident="ghcr.io/offspot/hwclock:1.0",
            filesize=59412480,
            fullsize=59382985,
        )
        self.config["oci_images"].add(image)

        # add to compose
        self.compose["services"]["hwclock"] = {
            "image": image.source,
            "container_name": "hwclock",
            "pull_policy": "never",
            "read_only": True,
            "restart": "unless-stopped",
            "expose": ["80"],
            "cap_add": ["CAP_SYS_TIME"],
            "privileged": True,
        }

        self.reversed_services.add("hwclock")

    def add_zim(self, zim: ZimPackage):
        if zim not in self.dashboard_entries:
            self.dashboard_entries.append(zim)

        self.add_file(
            url_or_content=zim.download_url,
            to=str(CONTENT_TARGET_PATH / "zims" / zim.filename),
            via="direct",
            size=zim.download_size,
            is_url=True,
        )

        if self.with_kiwixserve:
            return

        self.with_kiwixserve = True

        image = OCIImage(
            ident="ghcr.io/offspot/kiwix-serve:3.4.0",
            filesize=29194240,
            fullsize=29162475,
        )
        self.config["oci_images"].add(image)

        # add to compose
        self.compose["services"]["kiwix"] = {
            "image": image.source,
            "container_name": "kiwix",
            "pull_policy": "never",
            "restart": "unless-stopped",
            "expose": ["80"],
            "volumes": [
                {
                    "type": "bind",
                    "source": "/data/contents/zims",
                    "target": "/data",
                    "read_only": True,
                }
            ],
            "command": '/bin/sh -c "kiwix-serve --blockexternal '
            '--port 80 --nodatealiases /data/*.zim"',
        }

        if self.dashboard_offers_zim_downloads:
            self.add_files_service()
            self.files_mapping.update({"zim-downloads": "zims"})

        self.reversed_services.add("kiwix")

    def add_app(self, package: AppPackage):
        if package.kind != "app":
            raise ValueError(f"Package {package.ident} is not an app")

        if package.ident in self.compose["services"]:
            return

        # add file if app includes one
        if package.has_file():
            self.config["files"].append(package.as_fileconfig())

        self.config["oci_images"].add(package.oci_image)
        self.compose["services"][package.ident] = {
            "image": package.oci_image.source,
            "container_name": package.domain,
            "pull_policy": "never",
            "restart": "unless-stopped",
            "expose": ["80"],
        }

        self.reversed_services.add(package.domain)

    def add_files_package(self, package: FilesPackage):
        # add package to dashboard for a link
        if package in self.dashboard_entries:
            return
        self.dashboard_entries.append(package)

        # add to files so it gets downloaded
        if package.as_fileconfig() not in self.config["files"]:
            self.config["files"].append(package.as_fileconfig())

        self.add_files_service()

        # add to package_entries to it gets its endpoint in reverse proxy
        if package not in self.file_entries:
            self.file_entries.append(package)

        self.files_mapping.update({package.domain: package.ident})

        self.reversed_services.add("files")

    def add_files_service(self):
        # add image to compose
        if not self.with_files:
            image = OCIImage(
                ident="ghcr.io/offspot/file-browser:1.0",
                filesize=47226880,
                fullsize=47162907,
            )

            # add to compose
            self.config["oci_images"].add(image)
            self.compose["services"]["files"] = {
                "image": image.source,
                "container_name": "files",
                "pull_policy": "never",
                "restart": "unless-stopped",
                "expose": ["80"],
                "volumes": [
                    {
                        "type": "bind",
                        "source": "/data/contents/files",
                        "target": "/data",
                        "read_only": True,
                    }
                ],
            }

            self.with_files = True

    def add_file(
        self,
        *,
        url_or_content: str,
        to: str,
        via: str,
        size: int,
        is_url: bool | None = True,
    ):
        self.config["files"].append(
            FileConfig(
                **{
                    "url" if is_url else "content": url_or_content,
                    "to": to,
                    "via": via,
                    "size": size,
                }
            )
        )

    def render(self) -> str:
        """compute config based on requests"""
        ...

        # add kiwix apps?

        # gen dashboard.yaml
        if self.with_dashboard:
            self.gen_dashboard_config()

        # update reverseproxy config
        # > domain to subfolder for all files packages + zim-dl
        self.compose["services"]["reverse-proxy"]["environment"].update(
            {
                "SERVICES": ",".join(self.reversed_services),
                "FILES_MAPPING": ",".join(
                    f"{domain}:{folder}"
                    for domain, folder in self.files_mapping.items()
                ),
            }
        )

        # render compose

        # compute output size
        # self.config["output"] = get_size_for(self.config)

        return yaml_dump(self.config)
