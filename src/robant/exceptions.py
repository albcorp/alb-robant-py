#! /usr/bin/python

"""Exceptions for Robant

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

Exceptions to report failure conditions during operations to validate
state model and project hierarchy

"""

__docformat__ = "restructuredtext"


class HierarchyError(Exception):
    "Error in directory structure in project hierarchy"

    def __init__(self, file, message):
        self.file = str(file)
        self.message = message


class ModelPartitionError(ValueError):
    "TODO state classes intersect"

    def __init__(self, file, message):
        self.file = file
        self.message = message


class ModelValidityError(ValueError):
    "Invalid TODO state constraints"

    def __init__(self, file, message):
        self.file = file
        self.message = message


class ModelSatisfactionError(ValueError):
    "Unsatisfiable TODO state constraints"

    def __init__(self, file, message):
        self.file = file
        self.message = message


class ProjectIdentityError(ValueError):
    "Project identity information is invalid"

    def __init__(self, file, message):
        self.file = str(file)
        self.message = message


class ProjectStateError(ValueError):
    "Project or action TODO state is unknown"

    def __init__(self, file, message):
        self.file = str(file)
        self.message = message


class ProjectChronologyError(ValueError):
    "Timestamp on logbook entry is invalid"

    def __init__(self, file, message):
        self.file = str(file)
        self.message = message


class ProjectSatisfactionError(ValueError):
    "Project actions do not satisfy constraints on project state"

    def __init__(self, file, message):
        self.file = str(file)
        self.message = message
