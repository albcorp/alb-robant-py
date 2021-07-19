#! /usr/bin/python

"""Functions to test the `check` subcommand implementation

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

"""

__docformat__ = "restructuredtext"


from robant.helpers import getMetadataSchema, isValidSchema, isRootMetadata


def test_getMetadataSchema():
    schema = getMetadataSchema()
    assert isValidSchema(schema)


def test_isRootMetadata():
    assert isRootMetadata("./tests/data/tree-00/METADATA.yml")
    assert not isRootMetadata("./tests/data/tree-00/limb-00-00/METADATA.yml")
    assert not isRootMetadata("./tests/data/tree-00/limb-00-01/METADATA.yml")
