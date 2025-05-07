from __future__ import annotations

import re
from pathlib import PurePath as Path
from typing import Any

from offspot_config.catalog import app_catalog, get_app_path
from offspot_config.constants import (
    CONTENT_TARGET_PATH,
    DATA_PART_PATH,
    INTERNAL_BRANDING_PATH,
)
from offspot_config.inputs.base import BaseConfig
from offspot_config.inputs.checksum import Checksum
from offspot_config.inputs.file import FileConfig
from offspot_config.inputs.str import BlockStr
from offspot_config.oci_images import OCIImage
from offspot_config.packages import AppPackage, FilesPackage, ZimPackage
from offspot_config.utils.dashboard import Link, Reader
from offspot_config.utils.misc import b64_encode
from offspot_config.utils.sizes import (
    get_margin_for,
    get_min_image_size_for,
    get_raw_content_size_for,
)
from offspot_config.utils.yaml import yaml_dump
from offspot_runtime.__about__ import __version__

# matches $environ[XXX] where XXX is a builder-level environ to replace with
RE_ENVIRON_VAR = re.compile(r"\$environ{(?P<var>[A-Za-z_\-0-9]+)}")
RE_SPECIFIC_APP_DIR = re.compile(r"\${APP_DIR:(?P<ident>[a-z\.\-]+)}")

# service subdomain for ZIM downloads, when enabled
ZIMDL_PREFIX = "zim-download"
# service subdomain for kiwix-serve (used to be static to kiwix)
KIWIX_PREFIX = "browse"
# on-host path to dashboard config
DASHBOARD_CONFIG_PATH = CONTENT_TARGET_PATH / "dashboard.yaml"
# on-host metrics persistent data folder
METRICS_DATA_PATH = CONTENT_TARGET_PATH / "metrics"
# on-host metrics transient (tmpfs) log folders (caddy-created)
KIWIXSERVE_DATA_PATH = CONTENT_TARGET_PATH / "zims"
METRICS_VAR_LOG_PATH_HOST = Path("/var/log/metrics")
METRICS_VAR_LOG_PATH_CONT = Path("/var/log/host/metrics")
# hotspot original branding material (usually kept as untouched)
ORIGINAL_BRANDING_PATH = DATA_PART_PATH / "branding"
# actual hotspot branding. default from orig, replaced in builder
BRANDING_PATH = CONTENT_TARGET_PATH / "branding"

KIWIX_ZIM_LOAD_BALANCER_URL = "https://download.kiwix.org/zim/"

# data source for “internal images” (out of catalog)
INTERNAL_IMAGES = {
    "captive-portal": {
        "source": "ghcr.io/offspot/captive-portal:1.5.3",
        "filesize": 179998720,
        "fullsize": 179925549,
    },
    "dashboard": {
        "source": "ghcr.io/offspot/dashboard:1.6.2",
        "filesize": 177602560,
        "fullsize": 177484766,
    },
    "file-browser": {
        "source": "ghcr.io/offspot/file-browser:1.1",
        "filesize": 13629440,
        "fullsize": 13598399,
    },
    "hwclock": {
        "source": "ghcr.io/offspot/hwclock:1.2",
        "filesize": 58951680,
        "fullsize": 58922600,
    },
    "kiwix-serve": {
        "source": "ghcr.io/offspot/kiwix-serve:3.7.0-2",
        "filesize": 58480640,
        "fullsize": 58447802,
    },
    "metrics": {
        "source": "ghcr.io/offspot/metrics:0.3.0",
        "filesize": 167311360,
        "fullsize": 167202612,
    },
    "reverse-proxy": {
        "source": "ghcr.io/offspot/reverse-proxy:1.11",
        "filesize": 108257280,
        "fullsize": 108177344,
    },
}


def get_internal_image(ident: str) -> OCIImage:
    """OCI Image from special key identifying internal image"""
    if ident == "file-manager":
        return app_catalog.get_apppackage("file-manager.offspot.kiwix.org").oci_image
    entry = INTERNAL_IMAGES[ident]
    return OCIImage(
        ident=entry["source"], filesize=entry["filesize"], fullsize=entry["fullsize"]
    )


class ConfigBuilder:
    def __init__(
        self,
        *,
        base: BaseConfig,
        name: str = "My Offspot",
        tld: str | None = "offspot",
        domain: str | None = "my-offspot",
        welcome_domain: str | None = "goto.kiwix",
        ssid: str | None = "my-offspot",
        passphrase: str | None = None,
        timezone: str | None = "UTC",  # noqa: ARG002
        as_gateway: bool | None = False,
        environ: dict[str, str] | None = None,
        write_config: bool | None = False,
        kiwix_zim_mirror: str | None = None,
        public_version: str | None = None,
    ):
        self.name = name
        self.environ = environ or {}
        self.config: dict[str, Any] = {
            "base": {"source": base.source, "rootfs_size": base.rootfs_size},
            "output": {"size": "auto"},
            "oci_images": set(),
            "files": [],
            "write_config": write_config,
            "offspot": {
                "timezone": "UTC",
                "hostname": domain,
                "ethernet": {"type": "dhcp"},
                "ap": {
                    "domain": domain,
                    "welcome": welcome_domain,
                    "tld": tld,
                    "ssid": ssid,
                    "passphrase": passphrase,
                    "as-gateway": as_gateway,
                },
                "containers": {"name": "offspot", "services": {}},
            },
        }

        # Kiwix mirror URL (/ ending) to replace load-balancer URL with for ZIM download
        self.kiwix_zim_mirror = kiwix_zim_mirror
        # whether dashboard will offer downloads for ZIM files
        self.dashboard_offers_zim_downloads = True
        # list of reader entries to include in dashboard config
        self.dashboard_readers: list[Reader] = []
        # list of arbitrary links to display in dashboard
        self.dashboard_links: list[Link] = []
        # every card the dashboard will display
        self.dashboard_entries = []
        # advertised version for the Hotspot stack. defaults to ours
        self.public_version = (
            str(public_version) if public_version else f"v{__version__}"
        )

        # domain of services that must be reversed to (all but special cases)
        # either domain or domain:target-domain:target-port
        self.reversed_services: set[str] = set()
        # domain: folder map of virtual services serving only files
        self.files_mapping: dict[str, str] = {}
        # domain: (username, password) map of services to password protect
        self.protected_services: dict[str, tuple[str, str]] = {}
        # list(set) of paths we've added a .touch file for
        self.touched_path: set[Path] = set()

        self.with_kiwixserve: bool = False
        self.with_files: bool = False
        self.with_reverseproxy: bool = False
        self.with_dashboard: bool = False
        self.with_captive_portal: bool = False
        self.with_hwclock: bool = False
        self.with_metrics: bool = False

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

    def set_output_size(self, size: int):
        self.config["output"]["size"] = size

    def ensure_host_path(self, path: Path):
        if path not in self.touched_path:
            self.touched_path.add(path)

            self.add_file(
                url_or_content="-",
                to=f"{path}/.touch",
                size=1,
                via="direct",
                is_url=False,
            )

    def add_dashboard(
        self,
        *,
        allow_zim_downloads: bool | None = None,
        readers: list[Reader] | None = None,
        links: list[Link] | None = None,
    ):
        # only override options if set to a value (might have been set before)
        if allow_zim_downloads is not None:
            self.dashboard_offers_zim_downloads = allow_zim_downloads
        if readers is not None:
            self.dashboard_readers = readers
        if links is not None:
            self.dashboard_links = links

        if self.with_dashboard:
            return

        self.with_dashboard = True

        # Add files for requested readers
        for reader in self.dashboard_readers:
            self.add_file(
                url_or_content=reader.download_url,
                to=str(KIWIXSERVE_DATA_PATH / reader.filename),
                via="direct",
                size=reader.size,
                checksum=reader.checksum,
                is_url=True,
            )

        image = get_internal_image("dashboard")
        self.config["oci_images"].add(image)

        # add to compose
        self.compose["services"]["home"] = {
            "image": image.source,
            "container_name": "home",
            "pull_policy": "never",
            "restart": "unless-stopped",
            "expose": ["80"],
            "environment": {
                "KIWIX_READER_LINK_TPL": f"//{KIWIX_PREFIX}."
                + "{fqdn}/viewer#{zim_name}",
                "KIWIX_DOWNLOAD_LINK_TPL": (
                    f"//{ZIMDL_PREFIX}." + "{fqdn}/{zim_filename}"
                ),
            },
            "volumes": [
                # mandates presence of this file on host.
                # added in render() conditionnaly (if dashboard)
                # as it needs to list all content
                {
                    "type": "bind",
                    "source": str(DASHBOARD_CONFIG_PATH),
                    "target": "/src/home.yaml",
                    "read_only": False,
                },
                {
                    "type": "bind",
                    "source": f"{CONTENT_TARGET_PATH}/zims",
                    "target": "/data/zims",
                    "read_only": True,
                },
                {
                    "type": "bind",
                    "source": BRANDING_PATH,
                    "target": "/var/www/branding",
                    "read_only": True,
                },
                {
                    "type": "bind",
                    "source": ORIGINAL_BRANDING_PATH,
                    "target": "/var/www/offspot.branding",
                    "read_only": True,
                },
            ],
        }

        # add placeholder file to host fs to ensure bind succeeds
        self.ensure_host_path(KIWIXSERVE_DATA_PATH)

    def gen_dashboard_config(self):
        """Generate and add YAML config file for dashboard, based on entries"""

        if self.dashboard_offers_zim_downloads:
            download_fqdn = f"{ZIMDL_PREFIX}.{self.fqdn}"
        else:
            download_fqdn = None

        payload = {
            "metadata": {
                "name": self.name,
                "fqdn": self.fqdn,
                "version": self.public_version,
            },
            "packages": [
                package.to_dashboard_entry(
                    fqdn=self.fqdn,
                    kiwix_domain=KIWIX_PREFIX,
                    download_fqdn=download_fqdn,
                )
                for package in self.dashboard_entries
            ],
        }

        if self.dashboard_readers:
            payload["readers"] = [
                reader.to_dashboard_dict(download_fqdn=f"{ZIMDL_PREFIX}.{self.fqdn}")
                for reader in sorted(self.dashboard_readers, key=Reader.sort)
            ]

        if self.dashboard_links:
            payload["links"] = [link.to_dict() for link in self.dashboard_links]
            # resolve variables in link (for FQDN mostly)
            for link in payload["links"]:
                link["url"] = self.resolved_variable(text=link["url"])

        yaml_str = yaml_dump(payload)
        self.add_file(
            url_or_content=BlockStr(yaml_str),
            to=str(CONTENT_TARGET_PATH / "dashboard.yaml"),
            size=len(yaml_str.encode("utf-8")),
            via="direct",
            is_url=False,
        )

    def add_reverseproxy(self):
        if self.with_reverseproxy:
            return

        self.with_reverseproxy = True

        image = get_internal_image("reverse-proxy")
        self.config["oci_images"].add(image)

        # add to compose
        self.compose["services"]["reverse-proxy"] = {
            "image": image.source,
            "container_name": "reverse-proxy",
            "environment": {
                "FQDN": self.fqdn,
                "WELCOME_FQDN": (
                    f'{self.config["offspot"]["ap"]["welcome"]}.'
                    f'{self.config["offspot"]["ap"]["tld"]}'
                ),
                "METRICS_LOGS_DIR": str(METRICS_VAR_LOG_PATH_CONT),
            },
            "pull_policy": "never",
            "restart": "unless-stopped",
            "ports": ["80:80", "443:443"],
            "volumes": [
                # we are not binding METRICS_VAR_LOG_PATH directly because it resides
                # inside /var/log on host as this is a tmpfs so created on start, empty
                # and we want to keep it a tmpsfs, reachable from proxy and metrics.
                # So we bind /var/log (mostly empty on systemd anyway) and the proxy
                # will create the subfolder to write logs into
                {
                    "type": "bind",
                    "source": str(METRICS_VAR_LOG_PATH_HOST.parent),
                    "target": str(METRICS_VAR_LOG_PATH_CONT),
                    "read_only": False,
                },
                {
                    "type": "bind",
                    "source": BRANDING_PATH,
                    "target": "/var/www/branding",
                    "read_only": True,
                },
                {
                    "type": "bind",
                    "source": ORIGINAL_BRANDING_PATH,
                    "target": "/var/www/offspot.branding",
                    "read_only": True,
                },
            ],
        }

    def add_captive_portal(self):
        """enable captive-portal feature. WARN: check doc if you use custom network"""
        if self.with_captive_portal:
            return

        self.with_captive_portal = True

        # use dedicated dhcp-range (that we'll capture)
        # we purposedly work on a /24 network over wlan AP so every client can reach Pi
        # but we assign dhcp addresses in the .128/25 network (comprised in the /24 one)
        # so packets coming from AP clients can be identified in Pi's router and
        # treated specially (for the captive portal)
        wlan0_address = "192.168.2.1"
        self.config["offspot"]["ap"].update(
            {
                "dhcp-range": "192.168.2.129,192.168.2.254,255.255.255.0,1h",
                "network": "192.168.2.0/24",
                "address": wlan0_address,
                "as-gateway": True,
            }
        )

        image = get_internal_image("captive-portal")
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
                "HOTSPOT_IP": wlan0_address,
                "HOTSPOT_FQDN": self.fqdn,
                "CAPTURED_NETWORKS": "192.168.2.128/25",
                "TIMEOUT": "60",
                "FILTER_MODULE": "portal_filter",
            },
            "pull_policy": "never",
            "restart": "unless-stopped",
            "expose": ["2080", "2443"],
            "volumes": [
                # mandates presence of this file on host
                # it's a mandatory file to use captive-portal with.
                # created in base-image
                {
                    "type": "bind",
                    "source": "/var/run/internet",
                    "target": "/var/run/internet",
                    "read_only": True,
                },
                {
                    "type": "bind",
                    "source": BRANDING_PATH,
                    "target": "/src/portal/branding",
                    "read_only": True,
                },
                {
                    "type": "bind",
                    "source": ORIGINAL_BRANDING_PATH,
                    "target": "/src/portal/offspot.branding",
                    "read_only": True,
                },
            ],
        }

    def add_metrics(self):
        if self.with_metrics:
            return

        # metrics requires dashboard (as it provides/updates list of packages)
        if not self.with_dashboard:
            self.add_dashboard()

        image = get_internal_image("metrics")
        self.config["oci_images"].add(image)

        in_container_packages_path = "/conf/packages.yaml"
        in_container_data = "/data"
        in_container_logwatcher_dir = f"{in_container_data}/logwatcher"
        in_container_db_path = f"{in_container_data}/database.db"
        self.compose["services"]["metrics"] = {
            "image": image.source,
            "container_name": "metrics",
            "depends_on": {
                "home": {"condition": "service_healthy", "restart": True}
            },  # depends on dashboard's rewriting of packages YAML
            "environment": {
                "ALLOWED_ORIGINS": f"http://metrics|http://metrics.{self.fqdn}",
                "PACKAGE_CONF_FILE": in_container_packages_path,
                "DATABASE_URL": f"sqlite+pysqlite:///{in_container_db_path}",
                "LOGWATCHER_DATA_FOLDER": in_container_logwatcher_dir,
                "REVERSE_PROXY_LOGS_LOCATION": str(METRICS_VAR_LOG_PATH_CONT),
                "REVERSE_PROXY_LOGS_PATTERN": "metrics*.json",
            },
            "pull_policy": "never",
            "restart": "unless-stopped",
            "expose": ["80"],
            "volumes": [
                # mandates presence of this folder on host (see reverse-proxy conf)
                {
                    "type": "bind",
                    "source": str(METRICS_VAR_LOG_PATH_HOST.parent),
                    "target": str(METRICS_VAR_LOG_PATH_CONT),
                    "read_only": False,
                },
                # mandates presence of this folder on host beforehand
                {
                    "type": "bind",
                    "source": str(METRICS_DATA_PATH),
                    "target": in_container_data,
                    "read_only": False,
                },
                # mandates its presence on host. taken care of by dashboard
                {
                    "type": "bind",
                    "source": str(DASHBOARD_CONFIG_PATH),
                    "target": in_container_packages_path,
                    "read_only": True,
                },
                {
                    "type": "bind",
                    "source": BRANDING_PATH,
                    "target": "/src/ui/branding",
                    "read_only": True,
                },
                {
                    "type": "bind",
                    "source": ORIGINAL_BRANDING_PATH,
                    "target": "/src/ui/offspot.branding",
                    "read_only": True,
                },
            ],
        }

        # add persistent metrics (and its logwatcher subfolder) to host for docker bind
        self.ensure_host_path(METRICS_DATA_PATH / "logwatcher")

        self.reversed_services.add("metrics")

    def add_hwclock(self):
        if self.with_hwclock:
            return

        self.with_hwclock = True

        # add image
        image = get_internal_image("hwclock")
        self.config["oci_images"].add(image)

        # add to compose
        self.compose["services"]["hwclock"] = {
            "image": image.source,
            "container_name": "hwclock",
            "pull_policy": "never",
            "read_only": True,
            "restart": "unless-stopped",
            "expose": ["80"],
            "privileged": True,
            "volumes": [
                {
                    "type": "bind",
                    "source": BRANDING_PATH,
                    "target": "/src/branding",
                    "read_only": True,
                },
                {
                    "type": "bind",
                    "source": ORIGINAL_BRANDING_PATH,
                    "target": "/src/offspot.branding",
                    "read_only": True,
                },
            ],
        }

        self.protected_services.update(
            {
                "hwclock": (
                    self.environ.get("ADMIN_USERNAME", ""),
                    self.environ.get("ADMIN_PASSWORD", ""),
                )
            }
        )
        self.reversed_services.add("hwclock")

    def add_zim(self, zim: ZimPackage):
        if self.kiwix_zim_mirror and zim.download_url.startswith(
            KIWIX_ZIM_LOAD_BALANCER_URL
        ):
            zim.download_url = (
                f"{self.kiwix_zim_mirror}"
                f"{zim.download_url[len(KIWIX_ZIM_LOAD_BALANCER_URL):]}"
            )
        if zim not in self.dashboard_entries:
            self.dashboard_entries.append(zim)

        self.add_file(
            url_or_content=zim.download_url,
            to=str(KIWIXSERVE_DATA_PATH / zim.filename),
            via="direct",
            size=zim.download_size,
            checksum=zim.download_checksum,
            is_url=True,
        )

        if self.with_kiwixserve:
            return

        self.with_kiwixserve = True

        image = get_internal_image("kiwix-serve")
        self.config["oci_images"].add(image)

        # add to compose
        self.compose["services"]["kiwix"] = {
            "image": image.source,
            "container_name": "kiwix",
            "pull_policy": "never",
            "restart": "unless-stopped",
            "expose": ["80"],
            "volumes": [
                # mandates presence of this folder on host
                # thus created below via a placeholder
                {
                    "type": "bind",
                    "source": f"{CONTENT_TARGET_PATH}/zims",
                    "target": "/data",
                    "read_only": True,
                },
                {
                    "type": "bind",
                    "source": BRANDING_PATH,
                    "target": "/branding",
                    "read_only": True,
                },
                {
                    "type": "bind",
                    "source": ORIGINAL_BRANDING_PATH,
                    "target": "/offspot.branding",
                    "read_only": True,
                },
            ],
            "command": '/bin/sh -c "kiwix-serve --blockexternal '
            '--port 80 --nodatealiases /data/*.zim"',
        }

        # add placeholder file to host fs to ensure bind succeeds
        self.ensure_host_path(KIWIXSERVE_DATA_PATH)

        if self.dashboard_offers_zim_downloads:
            self.add_files_service()
            self.files_mapping.update({ZIMDL_PREFIX: "zims"})

        self.reversed_services.add(f"{KIWIX_PREFIX}:kiwix")

        image = get_internal_image("file-manager")
        self.config["oci_images"].add(image)

        # add to compose
        self.compose["services"]["zim-manager"] = {
            "image": image.source,
            "container_name": "zim-manager",
            "pull_policy": "never",
            "restart": "unless-stopped",
            "expose": ["80"],
            "environment": {
                "ACCESS_MODE": "manager",
                "ADMIN_USERNAME": self.environ.get("ADMIN_USERNAME", ""),
                "ADMIN_PASSWORD": self.environ.get("ADMIN_PASSWORD", ""),
                "APP_URL": f"http://zim-manager.{self.fqdn}",
            },
            "volumes": [
                # mandates presence of this folder on host
                # thus created above via a placeholder
                {
                    "type": "bind",
                    "source": f"{CONTENT_TARGET_PATH}/zims",
                    "target": "/data",
                    "read_only": False,
                }
            ],
        }

        self.reversed_services.add("zim-manager")

    def add_app(self, package: AppPackage, environ: dict[str, str] | None = None):
        if package.kind != "app":
            raise ValueError(f"Package {package.ident} is not an app")

        if package in self.dashboard_entries:
            return
        self.dashboard_entries.append(package)

        if package.ident in self.compose["services"]:
            return

        # add file if app includes one
        if package.has_file():
            self.config["files"].append(package.as_fileconfig())

        self.config["oci_images"].add(package.oci_image)
        self.compose["services"][package.domain] = {
            "image": package.oci_image.source,
            "environment": {},
            "volumes": [],
            "container_name": package.domain,
            "pull_policy": "never",
            "restart": "unless-stopped",
            "expose": ["80"],
        }
        # add package-defined environ
        if package.environ:
            self.compose["services"][package.domain]["environment"].update(
                {
                    key: self.resolved_variable(value, package=package)
                    for key, value in package.environ.items()
                }
            )

        # pass-down expected environ from global environ
        if package.environ_map:
            for global_env, local_env in package.environ_map.items():
                self.compose["services"][package.domain]["environment"].update(
                    {
                        local_env: self.resolved_variable(
                            self.environ.get(global_env, ""), package=package
                        )
                    }
                )
        # apply custom environ
        if environ:
            self.compose["services"][package.domain]["environment"].update(
                {
                    key: self.resolved_variable(value, package=package)
                    for key, value in environ.items()
                }
            )

        # mount volumes
        if package.volumes:
            for volume in package.volumes:
                parts = volume.split(":", 2)
                host_path, container_path = parts[:2]
                read_only = len(parts) == 3 and "ro" in parts[-1]

                # mandates presence of this folder on host
                # thus creation via a placeholder below
                self.compose["services"][package.domain]["volumes"].append(
                    {
                        "type": "bind",
                        "source": self.get_resolved_host_path(package, host_path),
                        "target": container_path,
                        "read_only": read_only,
                    }
                )

                # add a placeholder file to host folder to ensure bind mount succeeds
                self.ensure_host_path(
                    Path(self.get_resolved_host_path(package, host_path))
                )

        # links
        if package.links:
            self.compose["services"][package.domain]["links"] = [
                self.resolved_variable(link, package=package) for link in package.links
            ]

        # add subdomain services to reverse proxy
        if package.sub_services:
            for sub_domain, sub_target in package.sub_services.items():
                target, port = sub_target.split(":", 1)
                self.reversed_services.add(
                    self.resolved_variable(
                        f"{sub_domain}.{package.domain}:{target}:{port}",
                        package=package,
                    )
                )

        # handle password protection
        if package.protected_by:
            self.protected_services.update(
                {
                    package.domain: (
                        self.resolved_variable(
                            package.protected_by[0], package=package
                        ),
                        self.resolved_variable(
                            package.protected_by[1], package=package
                        ),
                    )
                }
            )

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

        self.files_mapping.update({package.domain: f"files/{package.ident}"})

        self.reversed_services.add("files")

    def add_files_service(self):
        # add image to compose
        if not self.with_files:
            # add to compose
            image = get_internal_image("file-browser")
            self.config["oci_images"].add(image)
            self.compose["services"]["files"] = {
                "image": image.source,
                "container_name": "files",
                "pull_policy": "never",
                "restart": "unless-stopped",
                "expose": ["80"],
                "volumes": [
                    # mandates presence of this folder on host
                    # thus created below via a placeholder
                    {
                        "type": "bind",
                        "source": f"{CONTENT_TARGET_PATH}",
                        "target": "/data",
                        "read_only": True,
                    },
                    {
                        "type": "bind",
                        "source": BRANDING_PATH,
                        "target": "/branding",
                        "read_only": True,
                    },
                    {
                        "type": "bind",
                        "source": ORIGINAL_BRANDING_PATH,
                        "target": "/offspot.branding",
                        "read_only": True,
                    },
                ],
            }

            # add placeholder file to host fs to ensure bind succeeds
            self.ensure_host_path(CONTENT_TARGET_PATH)

            self.with_files = True

    def add_file(
        self,
        *,
        url_or_content: str,
        to: str,
        via: str,
        size: int,
        is_url: bool | None = True,
        checksum: Checksum | None = None,
    ):
        # @to param can reference a specific package's home
        app_dir_match = RE_SPECIFIC_APP_DIR.match(to)
        if app_dir_match:
            ident = app_dir_match.groupdict()["ident"]
            to = to.replace(
                "${APP_DIR:" + ident + "}", get_app_path(package=app_catalog[ident])
            )

        self.config["files"].append(
            FileConfig(
                **{
                    "url" if is_url else "content": url_or_content,
                    "to": to,
                    "via": via,
                    "size": size,
                    "checksum": checksum,
                }
            )
        )

    def resolved_variable(self, text: str, package: AppPackage | None = None) -> str:
        """dynamic-variables resolved string"""

        # replace $environ{XXX} mappings
        match = RE_ENVIRON_VAR.search(text)
        if match:
            repl = self.environ[match.groupdict()["var"]]
            text = RE_ENVIRON_VAR.sub(repl, text)
        resolved = (
            text.replace("${FQDN}", self.fqdn)
            .replace("${REVERSE_NAME}", "reverse-proxy")
            .replace("${BRANDING_PATH}", str(BRANDING_PATH))
            .replace("${ORIGINAL_BRANDING_PATH}", str(ORIGINAL_BRANDING_PATH))
        )
        if package:
            app_dir = get_app_path(package=package)
            resolved = (
                resolved.replace("${APP_DIR}", app_dir)
                .replace("${PACKAGE_IDENT}", package.ident)
                .replace("${PACKAGE_DOMAIN}", package.domain)
                .replace("${PACKAGE_FQDN}", f"{package.domain}.{self.fqdn}")
            )
        return resolved

    def get_resolved_host_path(self, package: AppPackage, host_path: str) -> str:
        """dynamic-variables resolved host path for package"""

        return self.resolved_variable(text=host_path, package=package)

    def get_min_size(self) -> int:
        """minimum size in bytes of the resulting image"""
        content_size = get_raw_content_size_for(
            images=self.config["oci_images"],
            files=[fc.file for fc in self.config["files"]],
        )

        return get_min_image_size_for(
            rootfs_size=self.config["base"]["rootfs_size"],
            content_size=content_size,
            margin=get_margin_for(content_size),
        )

    def render(self) -> str:
        """compute config based on requests"""
        ...

        # add original branding so apps can rely on it
        self.ensure_host_path(ORIGINAL_BRANDING_PATH)
        data = b""
        for fpath in INTERNAL_BRANDING_PATH.iterdir():
            data = fpath.read_bytes()
            self.add_file(
                url_or_content=b64_encode(data),
                to=str(ORIGINAL_BRANDING_PATH.joinpath(fpath.name)),
                via="base64",
                size=len(data),
                is_url=False,
            )
        del data

        # make sure branding folder exists for mounts
        self.ensure_host_path(BRANDING_PATH)

        # gen dashboard.yaml
        if self.with_dashboard:
            self.gen_dashboard_config()

        # update reverseproxy config
        # > domain to subfolder for all files packages + zim-dl
        if self.with_reverseproxy:
            self.compose["services"]["reverse-proxy"]["environment"].update(
                {
                    "SERVICES": ",".join(self.reversed_services),
                    "NO_HOME_SERVICES": f"{KIWIX_PREFIX}",
                    "FILES_MAPPING": ",".join(
                        f"{domain}:{folder}"
                        for domain, folder in self.files_mapping.items()
                    ),
                    "PROTECTED_SERVICES": ",".join(
                        f"{svc}:{creds[0]}:{creds[1]}"
                        for svc, creds in self.protected_services.items()
                    ),
                }
            )

        # render compose

        # compute output size
        # self.config["output"] = get_size_for(self.config)

        return yaml_dump(self.config)
