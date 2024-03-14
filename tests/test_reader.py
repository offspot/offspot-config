import pytest  # pyright: ignore [reportMissingImports]

from offspot_config.utils.dashboard import Reader

REALISTIC_VALUES = [
    (
        "linux",
        "https://download.kiwix.org/release/kiwix-desktop/kiwix-desktop_x86_64_2.3.1-4.appimage",
        "kiwix-desktop_x86_64_2.3.1-4.appimage",
        146629824,
    ),
    (
        "android",
        "https://download.kiwix.org/release/kiwix-android/kiwix-3.9.1.apk",
        "kiwix-3.9.1.apk",
        79629012,
    ),
    (
        "windows",
        "https://download.kiwix.org/release/kiwix-desktop/kiwix-desktop_windows_x64_2.3.1-2.zip",
        "kiwix-desktop_windows_x64_2.3.1-2.zip",
        126628211,
    ),
    (
        "macos",
        "https://download.kiwix.org/release/kiwix-desktop-macos/kiwix-desktop-macos_3.1.0.dmg",
        "kiwix-desktop-macos_3.1.0.dmg",
        16051402,
    ),
]


@pytest.mark.parametrize(
    "url, expected_filename",
    [
        (
            "https://download.kiwix.org/release/kiwix-desktop/kiwix-desktop_windows_x64_2.3.1-2.zip",
            "kiwix-desktop_windows_x64_2.3.1-2.zip",
        ),
        (
            "https://download.kiwix.org/release/kiwix-android/kiwix-3.9.1.apk",
            "kiwix-3.9.1.apk",
        ),
        (
            "https://download.kiwix.org/release/kiwix-desktop-macos/kiwix-desktop-macos_3.1.0.dmg",
            "kiwix-desktop-macos_3.1.0.dmg",
        ),
        (
            "https://download.kiwix.org/release/kiwix-desktop/kiwix-desktop_x86_64_2.3.1-4.appimage",
            "kiwix-desktop_x86_64_2.3.1-4.appimage",
        ),
        ("https://www.freecodecamp.org/news/css-unit-guide/", "css-unit-guide"),
    ],
)
def test_filename_from_url(url: str, expected_filename: str):
    assert Reader.filename_from_url(url) == expected_filename


def test_reader_is_tuple():
    platform = "windows"
    url = "http://some.tld/file"
    filename = "one"
    size = 4
    assert Reader(platform, url, filename, size) == (platform, url, filename, size)
    assert Reader(
        download_url=url, size=size, platform=platform, filename=filename
    ) == (platform, url, filename, size)
    assert isinstance(Reader(platform, url, filename, size), Reader)
    assert isinstance(Reader(platform, url, filename, size), tuple)
    tuple_ = (platform, url, filename, size)
    casted = Reader._make(tuple_)
    assert isinstance(casted, Reader)


@pytest.mark.parametrize("platform, download_url, filename, size", REALISTIC_VALUES)
def test_reader_using(platform: str, download_url: str, filename: str, size: int):
    assert Reader.using(platform, download_url) == Reader(
        platform, download_url, filename, size
    )
    assert Reader.using(platform=platform, download_url=download_url) == Reader(
        platform, download_url, filename, size
    )


@pytest.mark.parametrize("platform, download_url, filename, size", REALISTIC_VALUES)
def test_invalid_data(platform: str, download_url: str, filename: str, size: int):
    with pytest.raises(TypeError):
        Reader(platform, download_url, filename)  # pyright: ignore [reportCallIssue]
    with pytest.raises(TypeError):
        Reader(
            platform,
            download_url,
            filename,
            size,
            32,  # pyright: ignore [reportCallIssue]
        )
    with pytest.raises(TypeError):
        Reader(platform=platform)  # pyright: ignore [reportCallIssue]
    with pytest.raises(TypeError):
        Reader(download_url=download_url)  # pyright: ignore [reportCallIssue]
    with pytest.raises(TypeError):
        Reader.using(
            platform, download_url, filename, size  # pyright: ignore [reportCallIssue]
        )


def test_sort_order():
    readers = [Reader(*values) for values in REALISTIC_VALUES]
    sorted_readers = sorted(readers, key=Reader.sort)
    assert readers != sorted_readers
    assert [r.platform for r in sorted_readers] == [
        "windows",
        "android",
        "macos",
        "linux",
    ]


@pytest.mark.parametrize(
    "platform, download_url, filename, size, expected_dict",
    [
        (
            "android",
            "https://download.kiwix.org/release/kiwix-android/kiwix-3.9.1.apk",
            "kiwix-3.9.1.apk",
            79629012,
            {
                "platform": "android",
                "download_url": "https://download.kiwix.org/release/kiwix-android/kiwix-3.9.1.apk",
                "filename": "kiwix-3.9.1.apk",
                "size": 79629012,
            },
        ),
        (
            "windows",
            "https://download.kiwix.org/release/kiwix-desktop/kiwix-desktop_windows_x64_2.3.1-2.zip",
            "kiwix-desktop_windows_x64_2.3.1-2.zip",
            126628211,
            {
                "platform": "windows",
                "download_url": "https://download.kiwix.org/release/kiwix-desktop/kiwix-desktop_windows_x64_2.3.1-2.zip",
                "filename": "kiwix-desktop_windows_x64_2.3.1-2.zip",
                "size": 126628211,
            },
        ),
        (
            "macos",
            "https://download.kiwix.org/release/kiwix-desktop-macos/kiwix-desktop-macos_3.1.0.dmg",
            None,
            None,
            {
                "platform": "macos",
                "download_url": "https://download.kiwix.org/release/kiwix-desktop-macos/kiwix-desktop-macos_3.1.0.dmg",
                "filename": "kiwix-desktop-macos_3.1.0.dmg",
                "size": 16051402,
            },
        ),
    ],
)
def test_to_dict(platform, download_url, filename, size, expected_dict):
    if filename and size:
        reader = Reader(platform, download_url, filename, size)
    else:
        reader = Reader.using(platform=platform, download_url=download_url)
    assert reader.to_dict() == expected_dict
