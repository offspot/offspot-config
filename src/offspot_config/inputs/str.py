from __future__ import annotations

from offspot_config.utils.yaml import custom_yaml_repr


@custom_yaml_repr
class BlockStr(str):
    """A string containing a large amount of text, usually representing a file"""

    @staticmethod
    def __yaml_repr__(dumper, data):
        """represent BlockStr as multiline"""
        return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style="|")
