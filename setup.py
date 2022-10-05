#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

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
            "from offspot_config_lib import __version__; print(__version__)",
        ],
        env={"PYTHONPATH": root_dir.joinpath("src")},
        text=True,
        capture_output=True,
    ).stdout.strip()


setup(
    name="offspot-runtime-config",
    version="1.0.0",
    description="Offspot Runtime Configuration Scripts",
    long_description=read("README.md"),
    long_description_content_type="text/markdown; charset=UTF-8; variant=GFM",
    author="kiwix",
    author_email="reg@kiwix.org",
    url="https://github.com/offspot/runtine-config",
    keywords="offspot",
    license="GPLv3+",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=["PyYaml>=5.3,<7.0"],
    entry_points={
        "console_scripts": [
            "offspot-config-ap=offspot_runtime_config.ap:entrypoint",
            "offspot-config-containers=offspot_runtime_config.containers:entrypoint",
            "offspot-config-ethernet=offspot_runtime_config.ethernet:entrypoint",
            "offspot-config-hostname=offspot_runtime_config.hostname:entrypoint",
            "offspot-config-timezone=offspot_runtime_config.timezone:entrypoint",
            "offspot-config-fromfile=offspot_runtime_config.fromfile:entrypoint",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
    ],
    python_requires=">=3.9",
)
