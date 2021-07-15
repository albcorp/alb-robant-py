#! /usr/bin/python

"""Functions to traverse and validate project plans and metadata

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

Functions to read project metadata files and folder structure, and check that
metadata conforms to the project plans schema and satisifies simple
self-consistency constraints

"""

__docformat__ = "restructuredtext"


import json
import pkgutil
import re
from pathlib import Path

import icontract
import intervaltree
import jsonschema
import yaml

from robant.exceptions import (
    RepositoryError,
    MissingMetadataError,
    MissingPlansError,
)


# Constants for project hierarchy

PROJECT_EXCLUDE_DIRS = ["LIB", "SRC", "TMP"]
PROJECT_METADATA_NAME = "METADATA.yml"
PROJECT_GIT_NAME = ".git"

# Constants and singleton for metadata JSON schema.  Use
# `getMetadataSchema`

METADATA_SCHEMA_FNAME = "schema/metadata.json"
METADATA_SCHEMA_JSON = None

# Constants for parsing project actions in project plans
#
# Match a project plan action directive with anchoring to the start and end of
# line
# Consume 2 subexpressions as follows
#
# 1. (mandatory) TODO keyword, labelled `todo`
# 2. (mandatory) Title text, labelled `title`
PLANS_ACTION_PAT = (
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
PLANS_ACTION_RE = re.compile(PLANS_ACTION_PAT)


class NoDatesSafeLoader(yaml.SafeLoader):
    """YAML loader that does not interpret date strings

    See https://stackoverflow.com/a/37958106 for the explanation
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


# Load datetimes as strings to prevent problems when serialising as JSON
NoDatesSafeLoader.remove_implicit_resolver("tag:yaml.org,2002:timestamp")


@icontract.require(lambda: True)
def getMetadataSchema():
    """Get the JSON schema for project metadata

    :return: JSON schema for project plan metadata
    :rtype: dict

    """
    global METADATA_SCHEMA_JSON
    if not METADATA_SCHEMA_JSON:
        METADATA_SCHEMA_JSON = json.loads(
            pkgutil.get_data(__name__, METADATA_SCHEMA_FNAME)
        )
    return METADATA_SCHEMA_JSON


@icontract.require(lambda s: True)
def isValidSchema(s):
    """Is `s` a valid draft 4 JSON schema?

    :param s: Python representation of draft 4 JSON schema
    :return: Validity of `s` as a draft 4 JSON schema
    :rtype: bool

    """
    try:
        jsonschema.Draft4Validator.check_schema(s)
        return True
    except:
        return False


@icontract.require(lambda d: Path(d).is_dir())
def locateRepositoryRoot(d):
    """Search upward from `d` for Git repository root

    :param d: Filename of a directory
    :raises RepositoryError: If `d` is not within a Git repository
    :return: Filename of Git repository root
    :rtype: pathlib.Path

    """
    for e in (Path(d).resolve() / PROJECT_METADATA_NAME).parents:
        if (e / PROJECT_GIT_NAME).is_dir():
            return e
    raise RepositoryError(f"No repository found: {d}")


@icontract.require(lambda f: True)
def isRootMetadata(f):
    """Is `f` the metadata filename of a root project?

    Assume `f` is in a Git repository that contains the entire project
    hierarchy.  Return true iff `f` is the filename of a metadata file
    for a root project.  A *root project* is a project that is not
    contained by a super project

    :param f: Filename of regular file
    :return: Whether `f` is the metadata filename of a root project
    :rtype: bool

    """
    f = Path(f).resolve()
    g = f.parent / PROJECT_GIT_NAME
    e = f.parent.parent / PROJECT_METADATA_NAME
    if f.name != PROJECT_METADATA_NAME or not f.is_file():
        return False
    if not g.is_dir() and e.is_file():
        return False
    return True


@icontract.require(lambda f: True)
def isLimbMetadata(f):
    """Is `f` a metadata filename of a limb project?

    Assume `f` is in a Git repository that contains the entire project
    hierarchy.  Return true iff `f` is the filename of a metadata file
    for a limb project.  A *limb project* is a project that is contained
    by a super project and that contains sub projects

    :param f: Filename of regular file
    :return: Whether `f` is the metadata filename of a limb project
    :rtype: bool

    """
    f = Path(f).resolve()
    g = f.parent / PROJECT_GIT_NAME
    e = f.parent.parent / PROJECT_METADATA_NAME
    if f.name != PROJECT_METADATA_NAME or not f.is_file():
        return False
    if g.is_dir() or not e.is_file():
        return False
    for d in f.parent.iterdir():
        if (
            d.is_dir()
            and d.name not in PROJECT_EXCLUDE_DIRS
            and (d / PROJECT_METADATA_NAME).is_file()
        ):
            return True
    return False


@icontract.require(lambda f: True)
def isLeafMetadata(f):
    """Is `f` a filename of project leaf metadata?

    Assume `f` is in a Git repository that contains the entire project
    hierarchy.  Return true iff `f` is the filename of a metadata file
    for a leaf project.  A *leaf project* is a project that is contained
    by a super project and that contains no sub projects

    :param f: Filename of regular file
    :return: Whether `f` is the filename of a leaf metadata file
    :rtype: bool

    """
    f = Path(f).resolve()
    g = f.parent / PROJECT_GIT_NAME
    e = f.parent.parent / PROJECT_METADATA_NAME
    if f.name != PROJECT_METADATA_NAME or not f.is_file():
        return False
    if g.is_dir() or not e.is_file():
        return False
    for d in f.parent.iterdir():
        if (
            d.is_dir()
            and d.name not in PROJECT_EXCLUDE_DIRS
            and (d / PROJECT_METADATA_NAME).is_file()
        ):
            return False
    return True


@icontract.require(lambda d: Path(d).is_dir())
def yieldLabeledMetadata(d):
    """Yield metadata files from project hierarchy with position labels

    Walk the folders from `d`, and yield pairs of the form `(LABEL,
    PATH)` where

    `LABEL`
       Whether the project is a ``ROOT``, ``LIMB``, or ``LEAF`` in the
       project hierarchy in terms of `ROOT`, `LIMB`, `LEAF`.  See
       `isRootMetadata`, `isLimbMetadata`, and `isLeafMetadata` for details

    `PATH`
       The filename of the metadata file that defines the project

    :param d: Filename of a directory
    :return: Sequence of pairs of labels and metadata filenames where
       the labels are one of ``ROOT``, ``LIMB``, or ``LEAF``
    :rtype: collections.Iterable[pathlib.Path]

    """

    def hunt(f):
        "Check for root metadata at `f` and recur on subfolders"
        if f.is_file():
            yield "ROOT", f
            for d in f.parent.iterdir():
                if d.is_dir() and d.name not in PROJECT_EXCLUDE_DIRS:
                    yield from visit(d / PROJECT_METADATA_NAME)
        else:
            for d in f.parent.iterdir():
                if d.is_dir() and d.name not in PROJECT_EXCLUDE_DIRS:
                    yield from hunt(d / PROJECT_METADATA_NAME)

    def visit(f):
        "Check for limb or leaf metadata and recur on subfolders"
        if f.is_file():
            # Defer the yield until a child has been seen
            deferred = True
            for d in f.parent.iterdir():
                if d.is_dir() and d.name not in PROJECT_EXCLUDE_DIRS:
                    if deferred:
                        yield "LIMB", f
                        deferred = False
                    yield from visit(d / PROJECT_METADATA_NAME)
            if deferred:
                yield "LEAF", f
                deferred = False

    # Walk project hierarchy, and yield labelled metadata filenames
    f = Path(d).resolve() / PROJECT_METADATA_NAME
    g = f.parent / PROJECT_GIT_NAME
    e = f.parent.parent / PROJECT_METADATA_NAME
    if not f.is_file():
        yield from hunt(f)
    elif g.is_dir() or not e.is_file():
        yield from hunt(f)
    else:
        yield from visit(f)


@icontract.require(lambda d: Path(d).is_dir())
def validateMetadataForest(d):
    """Validate metadata for forest of project plans under `d`

    Walk the folders from `d`.  Validate metadata files against schema.
    Check uniqueness constraints on UUID.  Check TODO state constraints
    on projects and actions.  Check log record constraints on intervals
    and transitions

    :param d: Filename of a directory
    :raises RepositoryError: If `d` is not within a Git repository

    """

    def readActionStateMap(plans_src):
        "Collect map from TODO states to lists of titles for actions in `plans_src`"
        m = {}
        for line in plans_src:
            action_match = PLANS_ACTION_RE.match(line)
            if action_match:
                todo = action_match["todo"]
                titles = m.get(todo, []) + [action_match["title"]]
                m[todo] = titles
        return m

    def checkUuid(metadata):
        "Enforce UUID constraints on `metadata`"
        uuid = metadata["uuid"]
        if uuid in uuids:
            raise ValueError(f"Project UUID MUST be unique: {uuid}")
        uuids[uuid] = metadata

    def checkRoot(metadata):
        "Enforce todo-state constraints on `metadata` of root project"
        todo = metadata["todo"]
        uuid = metadata["uuid"]
        if todo != "ROOT":
            raise ValueError(
                f"Root project MUST be in 'ROOT' todo state: {uuid}: {todo}"
            )

    def checkLimb(metadata):
        "Enforce todo-state constraints on `metadata` of limb project"
        todo = metadata["todo"]
        uuid = metadata["uuid"]
        if todo != "LOOK":
            raise ValueError(
                f"Interior project MUST be in 'LOOK' todo state: {uuid}"
            )

    def checkLeaf(metadata):
        "Enforce todo-state constraints on `metadata` of leaf project"
        todo = metadata["todo"]
        uuid = metadata["uuid"]
        if todo == "ROOT":
            raise ValueError(
                f"Leaf project MUST NOT be in 'ROOT' todo state: {uuid}"
            )

    def checkLogConstraints(metadata):
        "Enforce log record constraints in `metadata`"
        uuid = metadata["uuid"]
        logbook = metadata["logbook"]

        # Enforce interval constraints on logbook entries
        for curr in filter(lambda e: "start" in e, logbook):
            curr_start = curr["start"]
            curr_stop = curr["stop"]
            if curr_stop < curr_start:
                raise ValueError(
                    f"Entries MUST span a non-negative interval: {uuid}: {curr_start}, {curr_stop}"
                )
            elif intervals[curr_start:curr_stop]:
                olap = next(iter(intervals[curr_start:curr_stop]))
                olap_start = max(curr_start, olap[0])
                olap_stop = min(curr_stop, olap[1])
                olap_uuid = olap[2]["uuid"]
                raise ValueError(
                    f"Entries MUST NOT overlap: {uuid}, {olap_uuid}: {olap_start}, {olap_stop}"
                )
            else:
                intervals[curr_start:curr_stop] = metadata

        # Enforce sequence constraints on logbook entries
        for curr in logbook[-1:]:
            if "at" not in curr or "from" in curr:
                raise ValueError(
                    f"First entry MUST record project inception: {uuid}"
                )
        for pred, curr in zip(logbook[-1::-1], logbook[-2::-1]):
            pred_stop = pred["stop"] if "stop" in pred else pred["at"]
            curr_start = curr["start"] if "start" in curr else curr["at"]
            if curr_start < pred_stop:
                raise ValueError(
                    f"Entry MUST NOT start before preceding entry: {uuid}: {curr_start}"
                )

    def checkActionConstraints(metadata, actions):
        "Enforce todo-state constraints on `metadata` and `actions`"
        uuid = metadata["uuid"]
        todo = metadata["todo"]
        if not set(actions.keys()).issubset(
            {"HOLD", "WAIT", "WORK", "QUIT", "DROP", "STOP"}
        ):
            raise ValueError(f"Unknown TODO state in project actions: {uuid}")
        if todo == "ROOT" or todo == "LOOK" or todo == "NOTE":
            if actions:
                raise ValueError(
                    f"Projects in {todo} state MUST NOT contain actions: {uuid}"
                )
        elif todo == "WATCH":
            if "HOLD" not in actions and "WAIT" not in actions:
                raise ValueError(
                    f"Projects in {todo} state MUST contain HOLD or WAIT actions: {uuid}"
                )
            if "WORK" in actions or "QUIT" in actions:
                raise ValueError(
                    f"Projects in {todo} state MUST NOT contain WORK or QUIT actions: {uuid}"
                )
        elif todo == "START":
            if "WORK" not in actions or len(actions["WORK"]) != 1:
                raise ValueError(
                    f"Projects in {todo} state MUST contain exactly one WORK action: {uuid}"
                )
            if "QUIT" in actions:
                raise ValueError(
                    f"Projects in {todo} state MUST NOT contain QUIT actions: {uuid}"
                )
        elif todo == "QUASH":
            if "QUIT" not in actions:
                raise ValueError(
                    f"Projects in {todo} state MUST contain at least one QUIT action: {uuid}"
                )
            if "HOLD" in actions or "WAIT" in actions or "WORK" in actions:
                raise ValueError(
                    f"Projects in {todo} state MUST NOT contain HOLD, WAIT, or WORK actions: {uuid}"
                )
        elif todo == "CLOSE":
            if (
                "HOLD" in actions
                or "WAIT" in actions
                or "WORK" in actions
                or "QUIT" in actions
            ):
                raise ValueError(
                    f"Projects in {todo} state MUST NOT contain HOLD, WAIT, WORK, or QUIT actions: {uuid}"
                )

    # Walk project hierarchy and validate projects
    uuids = {}
    intervals = intervaltree.IntervalTree()
    schema = getMetadataSchema()
    locateRepositoryRoot(d)
    for l, m in yieldLabeledMetadata(d):
        p = m.parent / "PLANS.rst"
        try:
            if not m.is_file():
                raise MissingMetadataError(f"Missing metadata file: {m}")
            if not p.is_file():
                raise MissingPlansError(f"Missing plans file: {p}")
            with open(m, "r") as metadata_src, open(p, "r") as plans_src:
                metadata = yaml.load(metadata_src, Loader=NoDatesSafeLoader)
                actions = readActionStateMap(plans_src)
                jsonschema.validate(metadata, schema)
                checkUuid(metadata)
                if l == "ROOT":
                    checkRoot(metadata)
                if l == "LIMB":
                    checkLimb(metadata)
                if l == "LEAF":
                    checkLeaf(metadata)
                checkLogConstraints(metadata)
                checkActionConstraints(metadata, actions)
        except Exception as err:
            print("\n\nFailed validation: {0}: {1}".format(m, err))


# Local Variables:
# ispell-local-dictionary: "american"
# End:
