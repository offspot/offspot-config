import pathlib
import shutil

DATA_PART_PATH: pathlib.Path = pathlib.Path("/data")
CONTENT_TARGET_PATH: pathlib.Path = DATA_PART_PATH / "content"
SUPPORTED_UNPACKING_FORMATS: list[str] = [f[0] for f in shutil.get_unpack_formats()]
