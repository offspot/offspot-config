from __future__ import annotations

import datetime
import re

import requests
import xmltodict

from offspot_config.packages import ZimPackage


def get_zim_package(ident: str):
    """retrieve package from its ID

    works off a full copy of the official catalog"""

    publisher, name, flavour = ident.split(":", 2)

    catalog_url = "https://library.kiwix.org"
    resp = requests.get(
        f"{catalog_url}/catalog/v2/entries", params={"name": name}, timeout=60
    )
    resp.raise_for_status()
    opds = xmltodict.parse(resp.content)

    # not a list should there be a single entry
    if not isinstance(opds["feed"]["entry"], list):
        opds["feed"]["entry"] = [opds["feed"]["entry"]]

    for entry in opds["feed"]["entry"]:
        catalog_flavour = entry.get("flavour") or ""
        catalog_publisher = entry.get("publisher", {}).get("name") or ""

        if catalog_flavour != flavour:
            continue
        if catalog_publisher != publisher:
            continue

        links = {link["@type"]: link for link in entry["link"]}
        version = datetime.datetime.fromisoformat(
            re.sub(r"[A-Z]$", "", entry["updated"])
        ).strftime("%Y-%m-%d")

        return ZimPackage(
            kind="zim",
            ident=ident,
            name=entry["name"],
            title=entry["title"],
            description=entry["summary"],
            languages=entry["language"].split(",") or ["eng"],
            tags=entry["tags"].split(";"),
            flavour=flavour,
            download_size=int(links["application/x-zim"]["@length"]),
            download_url=re.sub(r".meta4$", "", links["application/x-zim"]["@href"]),
            icon_url=catalog_url
            + links["image/png;width=48;height=48;scale=1"]["@href"],
            version=version,
        )

    raise OSError(f"Not Found: ZIM with ident {ident}")
