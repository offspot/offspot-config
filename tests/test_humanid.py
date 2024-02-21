import pytest  # pyright: ignore [reportMissingImports]

from offspot_config.zim import get_libkiwix_humanid


@pytest.mark.parametrize(
    "filename, humanid",
    [
        ("abc.zim", "abc"),
        ("ABC.zim", "abc"),
        ("âbç.zim", "abc"),
        ("ancient.zimbabwe", "ancient"),
        ("ab cd.zim", "ab_cd"),
        ("/Data/ZIM/abc.zim", "abc"),
        ("3+2.zim", "3plus2"),
    ],
)
def test_libkiwix_humanid(filename: str, humanid: str):
    assert get_libkiwix_humanid(filename) == humanid
