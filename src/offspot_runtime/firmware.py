#!/usr/bin/env python3

""" Sets machine's WiFi firmware(s) to use """

import argparse
import logging
import pathlib
import sys
from typing import Optional

from offspot_runtime.__about__ import __version__
from offspot_runtime.checks import FIRMWARES, is_valid_firmware_for
from offspot_runtime.configlib import (
    Config,
    colored,
    fail_invalid,
    get_progname,
    succeed,
    warn_unless_root,
)

NAME = pathlib.Path(__file__).stem
FIRMWARE_DIR = pathlib.Path("/lib/firmware/cypress")
MATRIX: dict[str, list[dict]] = {
    "brcm43455": [
        {
            "target": "cyfmac43455-sdio.bin",
            "candidates": {
                "raspios": "cyfmac43455-sdio.bin_raspios",
                "supports-19_2021-11-30": "brcmfmac43455-sdio.bin_2021-11-30_minimal",
                "supports-24_2021-10-05_noap+sta": (
                    "brcmfmac43455-sdio.bin_2021-10-05_3rd-trial-minimal"
                ),
                "supports-32_2015-03-01_unreliable": (
                    "brcmfmac43455-sdio.bin_2015-03-01_7.45.18.0_ub19.10.1"
                ),
            },
        },
        {
            "target": "cyfmac43455-sdio.clm_blob",
            "candidates": {
                "raspios": "cyfmac43455-sdio.clm_blob_raspios",
                "supports-19_2021-11-30": "brcmfmac43455-sdio.clm_blob_2021-11-17_rpi",
                "supports-24_2021-10-05_noap+sta": (
                    "brcmfmac43455-sdio.clm_blob_2021-11-17_rpi"
                ),
                "supports-32_2015-03-01_unreliable": (
                    "brcmfmac43455-sdio.clm_blob_2018-02-26_rpi"
                ),
            },
        },
    ],
    "brcm43430": [
        {
            "target": "cyfmac43430-sdio.bin",
            "candidates": {
                "raspios": "cyfmac43430-sdio.bin_raspios",
                "supports-30_2018-09-28": (
                    "brcmfmac43430-sdio.bin_2018-09-11_7.45.98.65"
                ),
            },
        },
        {
            "target": "cyfmac43430-sdio.clm_blob",
            "candidates": {
                "raspios": "cyfmac43430-sdio.clm_blob_raspios",
                "supports-30_2018-09-28": (
                    "brcmfmac43430-sdio.clm_blob_2018-09-11_7.45.98.65"
                ),
            },
        },
    ],
}
Config.init(NAME)
logger = Config.logger


def main(
    brcm43455: Optional[str] = "",
    brcm43430: Optional[str] = "",
) -> int:
    logging.info("Configuring WiFi Firmware")
    warn_unless_root()

    if brcm43455:
        check = is_valid_firmware_for(chipset="brcm43455", firmware=brcm43455)
        if not check.passed:
            fail_invalid(check.help_text)

    if brcm43430:
        check = is_valid_firmware_for(chipset="brcm43430", firmware=brcm43430)
        if not check.passed:
            fail_invalid(check.help_text)

    changed: bool = False

    if brcm43455:
        for file in MATRIX["brcm43455"]:
            new_firmware = FIRMWARE_DIR.joinpath(file["candidates"][brcm43455])
            current_firmware = FIRMWARE_DIR.joinpath(file["target"])
            # skip if already properly configured
            if (
                current_firmware.is_symlink()
                and current_firmware.readlink() == new_firmware
            ):
                continue
            current_firmware.unlink(missing_ok=True)
            current_firmware.symlink_to(new_firmware)
            changed = True

    if brcm43430:
        for file in MATRIX["brcm43430"]:
            new_firmware = FIRMWARE_DIR.joinpath(file["candidates"][brcm43430])
            current_firmware = FIRMWARE_DIR.joinpath(file["target"])
            # skip if already properly configured
            if (
                current_firmware.is_symlink()
                and current_firmware.readlink() == new_firmware
            ):
                continue
            current_firmware.unlink(missing_ok=True)
            current_firmware.symlink_to(new_firmware)
            changed = True

    if changed:
        Config.logger.info(colored("WiFi firmware updated", "green"))
        return 100  # request reboot

    return succeed("no firmware changed")


def entrypoint():
    parser = argparse.ArgumentParser(
        prog=get_progname(),
        description="Configure Pi's WiFi firmware",
    )
    parser.add_argument("-V", "--version", action="version", version=__version__)
    parser.add_argument("--debug", action="store_true", dest="debug")

    parser.add_argument(
        "--brcm43455",
        help="Firmware to use for brcm43455 chipset",
        choices=FIRMWARES["brcm43455"],
        dest="brcm43455",
        required=False,
    )

    parser.add_argument(
        "--brcm43430",
        help="Firmware to use for brcm43455 chipset",
        choices=FIRMWARES["brcm43430"],
        dest="brcm43430",
        required=False,
    )

    kwargs = dict(parser.parse_args()._get_kwargs())
    Config.set_debug(enabled=kwargs.pop("debug", False))

    try:
        sys.exit(main(**kwargs))
    except Exception as exc:
        if Config.debug:
            logger.exception(exc)
        else:
            logger.error(exc)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(entrypoint())
