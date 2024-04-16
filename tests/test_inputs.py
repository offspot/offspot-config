from offspot_config.inputs.mainconfig import MainConfig


def test_main_config(mini_config_yaml: str):
    main_config = MainConfig.read_from(mini_config_yaml)
    assert main_config
    assert len(main_config.all_files) == 3
    assert len(main_config.all_images) == 1
