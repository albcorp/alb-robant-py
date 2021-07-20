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
    ProjectUuidError,
    ProjectTodoError,
    LogTransitionError,
    LogSpanError,
    LogOverlapError,
    LogSequenceError,
    ActionForbiddenError,
    ActionMissingError,
    ActionTodoError,
)


# Constants for project hierarchy

PROJECT_EXCLUDE_DIRS = ["LIB", "SRC", "TMP"]
PROJECT_METADATA_NAME = "METADATA.yml"
PROJECT_GIT_NAME = ".git"

# Constants for TODO states

ACTION_TODO_STATES = {"HOLD", "WAIT", "WORK", "QUIT", "DROP", "STOP"}

# Constants and singleton for metadata JSON schema

METADATA_SCHEMA_FNAME = "schema/metadata.json"
METADATA_SCHEMA_JSON = None

# Constants for formatting errors

ERROR_WITH_FILE = "\nFailed validation: {0}: {1}"
ERROR_WITH_LN = "\nFailed validation: {0}:{1}: {2}"
ERROR_WITH_COL = "\nFailed validation: {0}:{1}:{2}: {3}"

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
    """YAML loader that ignores date strings and records line numbers

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

    def construct_mapping(self, node, deep=False):
        mapping = super(NoDatesSafeLoader, self).construct_mapping(
            node, deep=deep
        )
        # Add 1 so line numbering starts at 1
        mapping["__line__"] = node.start_mark.line + 1
        return mapping


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
def inRepository(f):
    """Is `f` a file within a Git repository

    :param f: Filename
    :return: Whether `f` is a filename of a file within a Git repository
    :rtype: bool

    """
    e = Path(f).resolve()
    if e.is_file():
        for d in e.parents:
            if (d / PROJECT_GIT_NAME).is_dir():
                return True
    return False


@icontract.require(lambda f: inRepository(f))
def isRootMetadata(f):
    """Is `f` the metadata filename of a root project?

    Return true iff `f` is the filename of a metadata file for a root
    project.  A *root project* is a project that is not contained by a
    super project

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


@icontract.require(lambda f: inRepository(f))
def isLimbMetadata(f):
    """Is `f` a metadata filename of a limb project?

    Return true iff `f` is the filename of a metadata file for a limb
    project.  A *limb project* is a project that is contained by a super
    project and that contains sub projects

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


@icontract.require(lambda f: inRepository(f))
def isLeafMetadata(f):
    """Is `f` a filename of project leaf metadata?

    Return true iff `f` is the filename of a metadata file for a leaf
    project.  A *leaf project* is a project that is contained by a super
    project and that contains no sub projects

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

    def yieldNumberedActions(plans_src):
        "Yield actions from `plans_src` as tuples of line number, TODO state, and title"
        for line, text in enumerate(plans_src, 1):
            action_match = PLANS_ACTION_RE.match(text)
            if action_match:
                yield (line, action_match["todo"], action_match["title"])

    def checkUuid(metadata):
        "Enforce UUID constraints on `metadata`"
        uuid = metadata["uuid"]
        if uuid in uuids:
            raise ProjectUuidError(f"Project UUID MUST be unique: {uuid}")
        uuids[uuid] = metadata

    def checkRoot(metadata):
        "Enforce todo-state constraints on `metadata` of root project"
        todo = metadata["todo"]
        uuid = metadata["uuid"]
        if todo != "ROOT":
            raise ProjectTodoError(
                f"Root project MUST be in 'ROOT' todo state: {todo}"
            )

    def checkLimb(metadata):
        "Enforce todo-state constraints on `metadata` of limb project"
        todo = metadata["todo"]
        uuid = metadata["uuid"]
        if todo != "LOOK":
            raise ProjectTodoError(
                f"Interior project MUST be in 'LOOK' todo state: {todo}"
            )

    def checkLeaf(metadata):
        "Enforce todo-state constraints on `metadata` of leaf project"
        todo = metadata["todo"]
        uuid = metadata["uuid"]
        if todo == "ROOT":
            raise ProjectTodoError(
                f"Leaf project MUST NOT be in 'ROOT' todo state: {todo}"
            )

    def checkLogConstraints(metadata):
        "Enforce log record constraints in `metadata`"
        uuid = metadata["uuid"]
        logbook = metadata["logbook"]

        # Enforce transition constraints
        transitions = [curr for curr in logbook if "at" in curr]
        if transitions[0]["to"] != metadata["todo"]:
            raise LogTransitionError(
                transitions[0].get("__line__", 1),
                f"Project TODO state must agree with most recent transition",
            )
        if transitions[-1] != logbook[-1] or "from" in transitions[-1]:
            raise LogTransitionError(
                transitions[-1].get("__line__", 1),
                f"First entry MUST record project inception",
            )
        for curr, succ in zip(transitions, transitions[1:]):
            if "from" not in curr:
                raise LogTransitionError(
                    curr.get("__line__", 1),
                    f"Every subsequent transition MUST record the 'from' state",
                )
            if curr["from"] != succ["to"]:
                raise LogTransitionError(
                    curr.get("__line__", 1),
                    f"The 'from' state MUST match the preceding 'to' state",
                )

        # Enforce interval constraints
        for curr in filter(lambda e: "start" in e, logbook):
            curr_start = curr["start"]
            curr_stop = curr["stop"]
            if curr_stop <= curr_start:
                raise LogSpanError(
                    curr.get("__line__", 1),
                    f"Entries MUST span a positive interval: {curr_start}, {curr_stop}",
                )
            elif intervals[curr_start:curr_stop]:
                olap = next(iter(intervals[curr_start:curr_stop]))
                olap_start = max(curr_start, olap[0])
                olap_stop = min(curr_stop, olap[1])
                olap_uuid = olap[2]["uuid"]
                raise LogOverlapError(
                    curr.get("__line__", 1),
                    f"Entries MUST NOT overlap: {uuid}, {olap_uuid}: {olap_start}, {olap_stop}",
                )
            else:
                intervals[curr_start:curr_stop] = metadata

        # Enforce sequence constraints
        for pred, curr in zip(logbook[-1::-1], logbook[-2::-1]):
            pred_stop = pred["stop"] if "stop" in pred else pred["at"]
            curr_start = curr["start"] if "start" in curr else curr["at"]
            if curr_start < pred_stop:
                raise LogSequenceError(
                    curr.get("__line__", 1),
                    f"Entry MUST NOT start before preceding entry: {curr_start}",
                )

    def checkActionConstraints(metadata, actions):
        "Enforce todo-state constraints on `metadata` and `actions`"
        uuid = metadata["uuid"]
        todo = metadata["todo"]
        actn_todos = {actn_todo for _, actn_todo, _ in actions}

        # Check absence of actions
        if (todo == "ROOT" or todo == "LOOK" or todo == "NOTE") and actions:
            raise ActionForbiddenError(
                actions[0][0],
                f"Projects in {todo} state MUST NOT contain actions",
            )

        # Check absence of action states
        for line, actn_todo, title in actions:
            if actn_todo not in ACTION_TODO_STATES:
                raise ActionTodoError(
                    line,
                    f"Unknown TODO state {actn_todo} in project actions",
                )
            elif (
                todo == "WATCH"
                and (actn_todo == "WORK" or actn_todo == "QUIT")
                or todo == "START"
                and actn_todo == "QUIT"
                or todo == "QUASH"
                and (
                    actn_todo == "HOLD"
                    or actn_todo == "WAIT"
                    or actn_todo == "WORK"
                )
                or todo == "CLOSE"
                and (
                    actn_todo == "HOLD"
                    or actn_todo == "WAIT"
                    or actn_todo == "WORK"
                    or actn_todo == "QUIT"
                )
            ):
                raise ActionTodoError(
                    line,
                    f"Projects in {todo} state MUST NOT contain {actn_todo} actions",
                )

        # Check existence of action states
        if (
            todo == "WATCH"
            and "HOLD" not in actn_todos
            and "WAIT" not in actn_todos
        ):
            raise ActionMissingError(
                f"Projects in {todo} state MUST contain at least one HOLD or WAIT action"
            )
        elif todo == "START" and "WORK" not in actn_todos:
            raise ActionMissingError(
                f"Projects in {todo} state MUST contain exactly one WORK action"
            )
        elif todo == "QUASH" and "QUIT" not in actn_todos:
            raise ActionMissingError(
                f"Projects in {todo} state MUST contain at least one QUIT action"
            )

        # Check cardinality of action states
        if todo == "START":
            lines = list(
                line for line, actn_todo, _ in actions if actn_todo == "WORK"
            )
            if len(lines) > 1:
                raise ActionTodoError(
                    lines[1],
                    f"Projects in {todo} state MUST contain exactly one WORK action",
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
                raise MissingMetadataError(f"Missing metadata file")
            if not p.is_file():
                raise MissingPlansError(f"Missing plans file")
            with open(m, "r") as metadata_src, open(p, "r") as plans_src:
                metadata = yaml.load(metadata_src, Loader=NoDatesSafeLoader)
                actions = list(yieldNumberedActions(plans_src))
                jsonschema.validate(metadata, schema)
                try:
                    checkUuid(metadata)
                except ValueError as err:
                    print(ERROR_WITH_FILE.format(m, err))
                try:
                    if l == "ROOT":
                        checkRoot(metadata)
                    if l == "LIMB":
                        checkLimb(metadata)
                    if l == "LEAF":
                        checkLeaf(metadata)
                except (ProjectUuidError, ProjectTodoError) as err:
                    print(ERROR_WITH_FILE.format(m, err))
                try:
                    checkLogConstraints(metadata)
                except (
                    LogTransitionError,
                    LogSpanError,
                    LogOverlapError,
                    LogSequenceError,
                ) as err:
                    print(ERROR_WITH_LN.format(m, err.line, err.message))
                try:
                    checkActionConstraints(metadata, actions)
                except (ActionForbiddenError, ActionTodoError) as err:
                    print(ERROR_WITH_LN.format(p, err.line, err.message))
                except ActionMissingError as err:
                    print(ERROR_WITH_LN.format(p, 1, err))
        except MissingMetadataError as err:
            print(ERROR_WITH_FILE.format(m, err))
        except MissingPlansError as err:
            print(ERROR_WITH_FILE.format(p, err))
        except yaml.YAMLError as err:
            if hasattr(err, "problem_mark"):
                mark = err.problem_mark
                print(
                    ERROR_WITH_COL.format(
                        m, mark.line + 1, mark.column + 1, err
                    )
                )
            else:
                print(ERROR_WITH_FILE.format(m, err))
        except Exception as err:
            print(ERROR_WITH_FILE.format(m, err))


# Local Variables:
# ispell-local-dictionary: "american"
# End:
