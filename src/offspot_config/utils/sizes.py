from __future__ import annotations

import math

from offspot_config.file import File
from offspot_config.inputs.mainconfig import MainConfig
from offspot_config.oci_images import OCIImage

ONE_GB = int(1e9)
ONE_GiB = 2**30


def round_for_cluster(size: int, cluster_size: int = 512) -> int:
    """rounded size to the next value dividable by cluster size (512 usually)"""
    if size % cluster_size == 0:
        return size
    return size - (size % cluster_size) + cluster_size


def get_sd_hardware_margin_for(size: int) -> int:
    """number of bytes we must keep free as the HW might not support it"""
    return math.ceil(size * 0.03 if size / ONE_GB <= 16 else 0.04)


def get_margin_for(content_size: int) -> int:
    """margin in bytes for such a content_size"""

    return int(0.1 * content_size)  # static 10% for now


def get_raw_content_size(config: MainConfig) -> int:
    """bare sum of all known content sizes, in bytes"""
    return get_raw_content_size_for(images=config.all_images, files=config.all_files)


def get_raw_content_size_for(images: list[OCIImage], files: list[File]) -> int:
    """in-image size requirement for content"""
    tar_images_size = sum([image.filesize for image in images])
    expanded_images_size = sum([image.fullsize for image in images])
    expanded_files_size = sum([file.fullsize for file in files])

    return sum([tar_images_size, expanded_images_size, expanded_files_size])


def get_min_image_size_for(rootfs_size: int, content_size: int, margin: int) -> int:
    """computed minimum size in bytes for a base image rootfs, content and margin"""
    return round_for_cluster(sum([rootfs_size, content_size, margin]))


def get_min_image_size(config: MainConfig) -> int:
    content_size = get_raw_content_size(config=config)
    return get_min_image_size_for(
        rootfs_size=config.rootfs_size,
        content_size=content_size,
        margin=get_margin_for(content_size),
    )
