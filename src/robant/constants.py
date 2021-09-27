#! /usr/bin/python

"""Constants for Robant

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

Constants used by the functions in the Robant libraries.  The variables
are collected in this module to prevent circular imports

"""


# Standard library modules

import re


# Paths in source code

METADATA_SCHEMA_FNAME = "schema/metadata.json"
STATES_SCHEMA_FNAME = "schema/states.json"


# Paths in project hierarchy

VCS_BNAME = ".git"
STATES_BNAME = "STATES.yml"
METADATA_BNAME = "METADATA.yml"
PLANS_BNAME = "PLANS.rst"
EXCLUDE_DIRS = ["LIB", "SRC", "TMP"]


# Recognisers for TODO states

STATE_PAT = r"^[A-Z]+$"
STATE_RE = re.compile(STATE_PAT)


# Recognisers for metadata components

UUID_PAT = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
UUID_RE = re.compile(UUID_PAT)
SLUG_PAT = r"^[0-9a-z]*(-[0-9a-z]+)*$"
SLUG_RE = re.compile(SLUG_PAT)
TAG_PAT = r"^[0-9A-Za-z]+(_[0-9A-Za-z]+)*$"
TAG_RE = re.compile(TAG_PAT)
STATE_PAT = r"^[A-Z]+$"
STATE_RE = re.compile(STATE_PAT)
LABEL_PAT = r"^(LIMB|LEAF)$"


# Recognisers for project actions

# Match a project plan action directive with anchoring to the start and end of
# line
# Consume 2 subexpressions as follows
#
# 1. (mandatory) TODO keyword, labelled `todo`
# 2. (mandatory) Title text, labelled `title`
ACTION_PAT = (
    # Anchor
    r"^"
    # Directive prefix
    r"\.\. +todo:: +"
    # Action TODO state
    r"(?P<todo>[A-Z]+) +"
    # Action title
    r"(?P<title>.*?) *"
    # Anchor
    r"$"
)
ACTION_RE = re.compile(ACTION_PAT)


# Format strings for error reports

ERROR_WITH_FILE = "\nFailed validation: {0}: {1}"
ERROR_WITH_LN = "\nFailed validation: {0}:{1}: {2}"
ERROR_WITH_COL = "\nFailed validation: {0}:{1}:{2}: {3}"
