import pytest  # pyright: ignore [reportMissingImports]

from offspot_config.zim import ZimIdentTuple, from_ident, to_ident


@pytest.mark.parametrize(
    "ident, publisher, name, flavour",
    [
        ("openZIM:grimgrains_en_all:", "openZIM", "grimgrains_en_all", ""),
        ("Kiwix:mali-pour-les-nuls_fr_all:", "Kiwix", "mali-pour-les-nuls_fr_all", ""),
        (
            "openZIM:wikipedia_fr_comics:nopic",
            "openZIM",
            "wikipedia_fr_comics",
            "nopic",
        ),
    ],
)
def test_from_ident_and_to_ident(ident: str, publisher: str, name: str, flavour: str):
    assert from_ident(ident) == ZimIdentTuple(publisher, name, flavour)
    assert from_ident(ident) == (publisher, name, flavour)
    assert to_ident(*from_ident(ident)) == ident
    zit = from_ident(ident)
    assert (
        to_ident(publisher=zit.publisher, name=zit.name, flavour=zit.flavour) == ident
    )
