#! /usr/bin/python

"""YAML parser customised to Robant

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

"""

__docformat__ = "restructuredtext"


# Standard library modules

from typing import TextIO


# Third party modules

from yaml import load, SafeLoader


class NoDatesSafeLoader(SafeLoader):
    """Simplified YAML loader

    See https://stackoverflow.com/a/37958106 for explanation
    """

    @classmethod
    def remove_implicit_resolver(cls, tag_to_remove):
        "Remove implicit resolvers for a particular tag"
        if not "yaml_implicit_resolvers" in cls.__dict__:
            cls.yaml_implicit_resolvers = cls.yaml_implicit_resolvers.copy()
        for first_letter, mappings in cls.yaml_implicit_resolvers.items():
            cls.yaml_implicit_resolvers[first_letter] = [
                (tag, regexp)
                for tag, regexp in mappings
                if tag != tag_to_remove
            ]


# Load datetimes as strings to prevent problems when serialising
NoDatesSafeLoader.remove_implicit_resolver("tag:yaml.org,2002:timestamp")


def load_yaml(src: TextIO):
    return load(src, Loader=NoDatesSafeLoader)
