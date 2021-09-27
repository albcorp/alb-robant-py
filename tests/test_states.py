#! /usr/bin/python

"""Functions to test the `states` module

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

"""

__docformat__ = "restructuredtext"


# Standard library modules

from collections.abc import Mapping


# Local modules

from robant.states import getModelSchema


def test_getModelSchema():
    schema = getModelSchema()
    assert isinstance(schema, Mapping)
