from typing import Optional

from docker_export import Image

# See image-creator/utils/oci_images.py


class OCIImage:
    kind: str = "image"  # Item interface

    def __init__(
        self, name: str, filesize: int, fullsize: int, url: Optional[str] = None
    ):
        self.oci: Image = Image.parse(name)
        self.url = url
        self.filesize = filesize
        self.fullsize = fullsize

    def __hash__(self):
        return hash(self.oci.fullname)

    def __eq__(self, value):
        return all(
            getattr(self, key) == getattr(value, key)
            for key in ("oci", "url", "filesize", "fullsize")
        )

    @property
    def size(self) -> int:  # Item interface
        return self.filesize

    @property
    def source(self) -> str:  # Item interface
        return str(self.oci)

    def __repr__(self):
        return f"{self.__class__.__name__}<{self.oci!r}>"

    def __str__(self):
        return str(self.oci)

    def to_dict(self):
        return {
            "ident": str(self.oci),
            "filesize": self.filesize,
            "fullsize": self.fullsize,
        }
