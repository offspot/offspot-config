from offspot_config.catalog import app_catalog


def test_catalog_parsed():
    assert len(app_catalog)
