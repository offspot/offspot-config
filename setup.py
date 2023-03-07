#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import os
import pathlib
import subprocess
import sys

from setuptools import find_packages, setup

root_dir = pathlib.Path(__file__).parent


def read(*names, **kwargs):
    with open(root_dir.joinpath(*names), "r") as fh:
        return fh.read()


def get_version():
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; "
            "from offspot_runtime.configlib import __version__; "
            "print(__version__, file=sys.stdout, flush=True)",
        ],
        env={
            "PYTHONPATH": root_dir.joinpath("src"),
            "SETUP_ONLY": os.getenv("SETUP_ONLY"),
        },
        text=True,
        capture_output=True,
    ).stdout.strip()


setup(
    name="offspot-runtime-config",
    version=get_version(),
    description="Offspot Runtime Configuration Scripts & Library",
    long_description=read("README.md"),
    long_description_content_type="text/markdown; charset=UTF-8; variant=GFM",
    author="kiwix",
    author_email="reg@kiwix.org",
    url="https://github.com/offspot/runtime-config",
    keywords="offspot",
    license="GPLv3+",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=["PyYaml>=5.3,<7.0", "tzdata>=2022.7", "iso3166>=2.1.1"],
    entry_points={
        "console_scripts": [
            "offspot-config-ap=offspot_runtime.ap:entrypoint",
            "offspot-config-containers=offspot_runtime.containers:entrypoint",
            "offspot-config-ethernet=offspot_runtime.ethernet:entrypoint",
            "offspot-config-hostname=offspot_runtime.hostname:entrypoint",
            "offspot-config-timezone=offspot_runtime.timezone:entrypoint",
            "toggle-dnsmasq-spoof=offspot_runtime.dnsmasqspoof:entrypoint",
            "offspot-config-fromfile=offspot_runtime.fromfile:entrypoint",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
    python_requires=">=3.9",
)
