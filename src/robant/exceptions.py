#! /usr/bin/python

"""Exceptions to traversel and validation of project plans and metadata

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

Exceptions to report failure conditions during operations to read
project metadata files and folder structure, and check that metadata
conforms to the project plans schema and satisifies simple
self-consistency constraints

"""

__docformat__ = "restructuredtext"


class RepositoryError(Exception):
    "Traversal attempted outside of a repository"
    pass


class MissingMetadataError(Exception):
    "Traversal encountered non-excluded folder with no project metadata"
    pass


class MissingPlansError(Exception):
    "Traversal encountered non-excluded folder with no project plans"
    pass
