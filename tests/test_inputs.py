from __future__ import annotations

import pytest  # pyright: ignore [reportMissingImports]

from offspot_config.inputs.checksum import Checksum
from offspot_config.inputs.mainconfig import MainConfig


def test_main_config(mini_config_yaml: str):
    main_config = MainConfig.read_from(mini_config_yaml)
    assert main_config
    assert len(main_config.all_files) == 3
    assert len(main_config.all_images) == 1


@pytest.mark.parametrize(
    "config, md5sum",
    [
        (
            """
---
base:
  source: http://yolo
  rootfs_size: 2638217216
  checksum:
    algo: md5
    value: 747fd0841b56d2d5158e0e65646b1be1
    kind: digest
output:
  size: auto
""",
            "747fd0841b56d2d5158e0e65646b1be1",
        ),
        (
            """
---
base:
  source: http://yolo
  rootfs_size: 2638217216
output:
  size: auto
""",
            None,
        ),
        (
            """
---
base:
  source: 1.2.1
  rootfs_size: 2638217216
output:
  size: auto
""",
            "bb6fdcee36678ffcc88431dd502dfc11",
        ),
        (
            """
---
base:
  source: 1.2.1
  rootfs_size: 2638217216
  checksum:
    algo: md5
    value: YOLO
    kind: digest
output:
  size: auto
""",
            "bb6fdcee36678ffcc88431dd502dfc11",
        ),
        (
            """
---
base:
  source: 1.0.0
  rootfs_size: 2638217216
output:
  size: auto
""",
            None,
        ),
    ],
)
def test_base_config(config: str, md5sum: str | None):
    main_config = MainConfig.read_from(config)
    assert main_config
    assert len(main_config.all_files) == 0
    assert len(main_config.all_images) == 0
    assert main_config.base
    assert main_config.base_file
    checksum = Checksum(algo="md5", value=md5sum) if md5sum else None
    assert main_config.base_file.checksum == checksum
