from __future__ import annotations

import datetime
import re
import unicodedata
from typing import NamedTuple

import requests
import xmltodict

from offspot_config.inputs.checksum import Checksum
from offspot_config.packages import ZimPackage
from offspot_config.utils.download import read_checksum_from


class ZimIdentTuple(NamedTuple):
    publisher: str
    name: str
    flavour: str = ""


def to_ident(publisher: str, name: str, flavour: str = "") -> str:
    """An ident from required information"""
    return f"{publisher}:{name}:{flavour}"


def from_ident(ident: str) -> ZimIdentTuple:
    """basic information from a ZIM ident"""
    publisher, name, flavour = ident.split(":", 2)
    return ZimIdentTuple(publisher=publisher, name=name, flavour=flavour)


def get_zim_package(ident: str):
    """retrieve package from its ID

    works off a full copy of the official catalog"""

    publisher, name, flavour = from_ident(ident)

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
        url = re.sub(r".meta4$", "", links["application/x-zim"]["@href"])

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
            download_url=url,
            download_checksum=Checksum(
                algo="md5", value=read_checksum_from(f"{url}.md5")
            ),
            icon_url=catalog_url
            + links["image/png;width=48;height=48;scale=1"]["@href"],
            version=version,
        )

    raise OSError(f"Not Found: ZIM with ident {ident}")


def get_libkiwix_humanid(filename: str) -> str:
    """libkiwix HumanID from a ZIM filename

    Equivalent to kiwix-serve “BookName” used in URLs and built from filename

    Implemented from libkiwix@86100b39"""

    def _remove_accents(text: str) -> str:
        """unaccented version of text as in kiwix::removeAccents"""

        # equivalent to ICU's Transliterator wkth "Lower; NFD; [:M:] remove; NFC"
        return unicodedata.normalize(
            "NFC",
            "".join(
                char
                for char in unicodedata.normalize("NFD", text.lower())
                if unicodedata.category(char) != "Mn"
            ),
        )

    ident = _remove_accents(filename)

    for replacement, pattern in [
        ("", r"^.*/"),  # remove leading path (we may not need this)
        ("", r"\.zim[a-z]*$"),  # remove suffix
        ("_", r" "),  # replace space with underscope
        ("plus", r"\+"),  # replace + with literal plus
    ]:
        ident = re.sub(pattern, replacement, ident)

    return ident
