import pytest  # pyright: ignore [reportMissingImports]


@pytest.fixture(scope="session")
def mini_config_yaml():
    yield """
---
base:
  source: https://drive.offspot.it/base/offspot-base-arm64-1.2.0.img
  rootfs_size: 2638217216
output:
  size: auto
oci_images:
- ident: ghcr.io/offspot/file-browser:1.1
  filesize: 13629440
  fullsize: 13598399
  url: null
files:
- to: /data/contents/zims/.touch
  content: |-
    -
  via: direct
  size: 1
- to: /data/contents/zims/kiwix-desktop-macos_3.1.0.dmg
  url: https://download.kiwix.org/release/kiwix-desktop-macos/kiwix-desktop-macos_3.1.0.dmg
  via: direct
  size: 16051402
  checksum:
    algo: md5
    value: 747fd0841b56d2d5158e0e65646b1be1
    kind: digest
- to: /data/contents/zims/wikipedia_ab_all_maxi_2024-02.zim
  url: https://mirror.download.kiwix.org/zim/wikipedia/wikipedia_ab_all_maxi_2024-02.zim
  via: direct
  size: 26634065
  checksum:
    algo: md5
    value: https://download.kiwix.org/zim/wikipedia/wikipedia_ab_all_maxi_2024-02.zim.md5
    kind: url
"""
