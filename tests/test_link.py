import pytest  # pyright: ignore [reportMissingImports]

from offspot_config.utils.dashboard import Link


def test_link_is_tuple():
    label = "Metrics"
    url = "://metrics.kiwix.hotspot"
    icon = "lock"
    assert Link(label, url) == (label, url, "")
    assert Link(label, url, icon) == (label, url, icon)
    assert Link(url=url, icon=icon, label=label) == (label, url, icon)
    assert isinstance(Link(label, url, icon), Link)
    assert isinstance(Link(label, url, icon), tuple)
    tuple_ = (label, url, icon)
    casted = Link._make(tuple_)
    assert isinstance(casted, Link)


@pytest.mark.parametrize(
    "label, url, icon, expected_dict",
    [
        (
            "Metrics",
            "://metrics.kiwix.hotspot",
            "",
            {
                "label": "Metrics",
                "url": "://metrics.kiwix.hotspot",
                "icon": "",
            },
        ),
        (
            "Admin",
            "://admin.kiwix.hotspot",
            "lock",
            {
                "label": "Admin",
                "url": "://admin.kiwix.hotspot",
                "icon": "lock",
            },
        ),
    ],
)
def test_to_dict(label, url, icon, expected_dict):
    if icon:
        link = Link(label, url, icon)
    else:
        link = Link(label=label, url=url)
    assert link.to_dict() == expected_dict
