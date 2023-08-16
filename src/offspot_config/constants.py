from __future__ import annotations

import pathlib
import shutil

DATA_PART_PATH: pathlib.Path = pathlib.Path("/data")
CONTENT_TARGET_PATH: pathlib.Path = DATA_PART_PATH / "contents"
SUPPORTED_UNPACKING_FORMATS: list[str] = [f[0] for f in shutil.get_unpack_formats()]
POST_EXPANSION_UNWANTED_PATTERNS = (
    ### Linux ###
    "*~",
    # temp files which can be created if process still has handle open of a deleted file
    ".fuse_hidden*",
    # KDE directory preferences
    ".directory",
    # Linux trash folder which might appear on any partition or disk
    ".Trash-*",
    # .nfs files are created when an open file is removed but is still being accessed
    ".nfs*",
    ### macOS ###
    ".DS_Store",
    ".AppleDouble",
    ".LSOverride",
    # Thumbnails
    "._*",
    # Files that might appear in the root of a volume
    ".DocumentRevisions-V100",
    ".fseventsd",
    ".Spotlight-V100",
    ".TemporaryItems",
    ".Trashes",
    ".VolumeIcon.icns",
    ".com.apple.timemachine.donotpresent",
    # Directories potentially created on remote AFP share
    ".AppleDB",
    ".AppleDesktop",
    "Network Trash Folder",
    ".apdisk",
    # iCloud generated files
    "*.icloud",
    ### Windows ###
    # Windows thumbnail cache files
    "Thumbs.db",
    "Thumbs.db:encryptable",
    "ehthumbs.db",
    "ehthumbs_vista.db",
    # Dump file
    "*.stackdump",
    # Folder config file
    "desktop.ini",
    "Desktop.ini",
    # Recycle Bin used on file shares
    "$RECYCLE.BIN",
    # Windows shortcuts
    "*.lnk",
)
