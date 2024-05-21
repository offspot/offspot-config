import pytest  # pyright: ignore [reportMissingImports]

from offspot_config.inputs.checksum import Checksum
from offspot_config.utils.dashboard import Reader

REALISTIC_VALUES = [
    (
        "linux",
        "https://download.kiwix.org/release/kiwix-desktop/kiwix-desktop_x86_64_2.3.1-4.appimage",
        "kiwix-desktop_x86_64_2.3.1-4.appimage",
        146629824,
        "899279fb76e357afe33bbdd968750376",
    ),
    (
        "android",
        "https://download.kiwix.org/release/kiwix-android/kiwix-3.9.1.apk",
        "kiwix-3.9.1.apk",
        79629012,
        "d2ede8e23b4095718c508f44a341f687",
    ),
    (
        "windows",
        "https://download.kiwix.org/release/kiwix-desktop/kiwix-desktop_windows_x64_2.3.1-2.zip",
        "kiwix-desktop_windows_x64_2.3.1-2.zip",
        126628211,
        "adf9b64b5c6906427d7a1c8bdfc31546",
    ),
    (
        "macos",
        "https://download.kiwix.org/release/kiwix-macos/kiwix-macos_3.1.0.dmg",
        "kiwix-macos_3.1.0.dmg",
        16051402,
        "747fd0841b56d2d5158e0e65646b1be1",
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
            "https://download.kiwix.org/release/kiwix-macos/kiwix-macos_3.1.0.dmg",
            "kiwix-macos_3.1.0.dmg",
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


def get_checksum_from(md5sum: str) -> Checksum:
    return Checksum(algo="md5", value=md5sum)


def test_reader_is_tuple():
    platform = "windows"
    url = "http://some.tld/file"
    filename = "one"
    size = 4
    checksum = None
    assert Reader(platform, url, filename, size, checksum) == (
        platform,
        url,
        filename,
        size,
        checksum,
    )
    assert Reader(
        download_url=url,
        size=size,
        platform=platform,
        filename=filename,
        checksum=checksum,
    ) == (platform, url, filename, size, checksum)
    assert isinstance(Reader(platform, url, filename, size, checksum), Reader)
    assert isinstance(Reader(platform, url, filename, size, checksum), tuple)
    tuple_ = (platform, url, filename, size, checksum)
    casted = Reader._make(tuple_)
    assert isinstance(casted, Reader)


@pytest.mark.parametrize(
    "platform, download_url, filename, size, md5sum", REALISTIC_VALUES
)
def test_reader_using(
    platform: str, download_url: str, filename: str, size: int, md5sum: str
):
    assert Reader.using(
        platform, download_url, checksum=get_checksum_from(md5sum)
    ) == Reader(
        platform,
        download_url,
        filename,
        size,
        get_checksum_from(md5sum),
    )
    assert Reader.using(platform=platform, download_url=download_url) == Reader(
        platform,
        download_url,
        filename,
        size,
        None,
    )
    assert Reader.using(platform=platform, download_url=download_url) == Reader(
        platform,
        download_url,
        filename,
        size,
    )


@pytest.mark.parametrize(
    "platform, download_url, filename, size, md5sum", REALISTIC_VALUES
)
def test_invalid_data(
    platform: str, download_url: str, filename: str, size: int, md5sum: str
):
    with pytest.raises(TypeError):
        Reader(platform, download_url, filename)  # pyright: ignore [reportCallIssue]
    with pytest.raises(TypeError):
        Reader(
            platform,
            download_url,
            filename,
            size,
            get_checksum_from(md5sum),
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
    readers = [
        Reader(*values[:-1], checksum=get_checksum_from(md5sum=values[-1]))
        for values in REALISTIC_VALUES
    ]
    sorted_readers = sorted(readers, key=Reader.sort)
    assert readers != sorted_readers
    assert [r.platform for r in sorted_readers] == [
        "windows",
        "android",
        "macos",
        "linux",
    ]


@pytest.mark.parametrize(
    "platform, download_url, filename, size, md5sum, expected_dict",
    [
        (
            "android",
            "https://download.kiwix.org/release/kiwix-android/kiwix-3.9.1.apk",
            "kiwix-3.9.1.apk",
            79629012,
            None,
            {
                "platform": "android",
                "download_url": "https://download.kiwix.org/release/kiwix-android/kiwix-3.9.1.apk",
                "filename": "kiwix-3.9.1.apk",
                "size": 79629012,
                "checksum": None,
            },
        ),
        (
            "windows",
            "https://download.kiwix.org/release/kiwix-desktop/kiwix-desktop_windows_x64_2.3.1-2.zip",
            "kiwix-desktop_windows_x64_2.3.1-2.zip",
            126628211,
            "adf9b64b5c6906427d7a1c8bdfc31546",
            {
                "platform": "windows",
                "download_url": "https://download.kiwix.org/release/kiwix-desktop/kiwix-desktop_windows_x64_2.3.1-2.zip",
                "filename": "kiwix-desktop_windows_x64_2.3.1-2.zip",
                "size": 126628211,
                "checksum": {
                    "algo": "md5",
                    "value": "adf9b64b5c6906427d7a1c8bdfc31546",
                    "kind": "digest",
                },
            },
        ),
        (
            "macos",
            "https://download.kiwix.org/release/kiwix-macos/kiwix-macos_3.1.0.dmg",
            None,
            None,
            None,
            {
                "platform": "macos",
                "download_url": "https://download.kiwix.org/release/kiwix-macos/kiwix-macos_3.1.0.dmg",
                "filename": "kiwix-macos_3.1.0.dmg",
                "size": 16051402,
                "checksum": None,
            },
        ),
    ],
)
def test_to_dict(platform, download_url, filename, size, md5sum, expected_dict):
    checksum = get_checksum_from(md5sum) if md5sum else None
    if filename and size:
        reader = Reader(platform, download_url, filename, size, checksum)
    else:
        reader = Reader.using(
            platform=platform, download_url=download_url, checksum=checksum
        )
    assert reader.to_dict() == expected_dict
