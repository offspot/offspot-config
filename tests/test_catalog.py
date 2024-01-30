from offspot_config.catalog import app_catalog


def test_catalog_parsed():
    assert len(app_catalog)


def test_catalog_packages_have_size():
    for package in app_catalog.values():
        assert package.size
