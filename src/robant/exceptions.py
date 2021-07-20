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


class ProjectUuidError(ValueError):
    "Non-unique project UUID"
    pass


class ProjectTodoError(ValueError):
    "Project at TODO state is incorrect for location in project hierarchy"
    pass


class LogTransitionError(ValueError):
    "Out of sequence TODO states in transition"

    def __init__(self, line, message):
        self.line = line
        self.message = message


class LogSpanError(ValueError):
    "Negative or zero time interval in logbook"

    def __init__(self, line, message):
        self.line = line
        self.message = message


class LogOverlapError(ValueError):
    "Overlapping intervals in logbooks of one or more projects"

    def __init__(self, line, message):
        self.line = line
        self.message = message


class LogSequenceError(ValueError):
    "Out of sequence entry in logbook"

    def __init__(self, line, message):
        self.line = line
        self.message = message


class ActionForbiddenError(ValueError):
    "Forbidden project action in project plans"

    def __init__(self, line, message):
        self.line = line
        self.message = message


class ActionMissingError(ValueError):
    "Missing project action in project plans"
    pass


class ActionTodoError(ValueError):
    "Unknown or unexpected TODO state in project plans"

    def __init__(self, line, message):
        self.line = line
        self.message = message
