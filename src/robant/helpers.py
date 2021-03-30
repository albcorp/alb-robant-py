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
from pathlib import Path

import icontract
import intervaltree
import jsonschema
import yaml

from robant.exceptions import RepositoryError, MissingMetadataError


# Constants for project hierarchy

PROJECT_EXCLUDE_DIRS = ["LIB", "SRC", "TMP"]
PROJECT_METADATA_NAME = "METADATA.yml"

# Constants and singleton for metadata JSON schema.  Use
# `getMetadataSchema`

METADATA_SCHEMA_FNAME = "schema/metadata.json"
METADATA_SCHEMA_JSON = None


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
        if (e / ".git").is_dir():
            return e
    raise RepositoryError(f"No repository found: {d}")


@icontract.require(lambda f: True)
def isPlanMetadata(f):
    """Is `f` a filename of project metadata?

    A *plan metadata* file contains the metadata of a project plan.
    Plan metadata does not distinquish between root, limb, or leaf of
    the project plan hierarchy.

    :param f: Filename of regular file
    :raises RepositoryError: If `f` is not within a Git repository
    :return: Whether `f` is the filename of a plan metadata file
    :rtype: bool

    """
    f = Path(f).resolve()
    if f.name != PROJECT_METADATA_NAME or not f.is_file():
        return False
    for d in f.parents:
        if (d / ".git").is_dir():
            return True
    raise RepositoryError(f"No repository found: {f}")


@icontract.require(lambda f: True)
def isRootMetadata(f):
    """Is `f` a filename of project root metadata?

    A *root metadata* file contains the metadata of a root project plan.
    A *root project plan* is one with no parent.

    :param f: Filename of regular file
    :raises RepositoryError: If `f` is not within a Git repository
    :return: Whether `f` is the filename of a root metadata file
    :rtype: bool

    """
    f = Path(f).resolve()
    if f.name != PROJECT_METADATA_NAME or not f.is_file():
        return False
    if (f.parent / ".git").is_dir():
        return True
    for d in f.parent.parents:
        if (d / PROJECT_METADATA_NAME).is_file():
            return False
        if (d / ".git").is_dir():
            return True
    raise RepositoryError(f"No repository found: {f}")


@icontract.require(lambda f: True)
def isLimbMetadata(f):
    """Is `f` a filename of project limb metadata?

    A *limb metadata* file contains the metadata of a limb project plan.
    A *limb project plan* is one with a parent.

    :param f: Filename of regular file
    :raises RepositoryError: If `f` is not within a Git repository
    :return: Whether `f` is the filename of a limb metadata file
    :rtype: bool

    """
    f = Path(f).resolve()
    q = locateRepositoryRoot(f.parent)
    return (
        f.name == PROJECT_METADATA_NAME
        and f.is_file()
        and f.parent != q
        and (f.parent.parent / PROJECT_METADATA_NAME).is_file()
    )


@icontract.require(lambda f: True)
def isLeafMetadata(f):
    """Is `f` a filename of project leaf metadata?

    A *leaf metadata* file contains the metadata of a leaf project plan.
    A *leaf project plan* is one with no children.

    :param f: Filename of regular file
    :raises RepositoryError: If `f` is not within a Git repository
    :return: Whether `f` is the filename of a leaf metadata file
    :rtype: bool

    """
    f = Path(f).resolve()
    q = locateRepositoryRoot(f.parent)
    if f.name != PROJECT_METADATA_NAME or not f.is_file():
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
def yieldRootMetadata(d):
    """Yield root metadata files from forest of project plans

    Walk the folders from `locateRepositoryRoot(d)`, and yield the
    filenames of root metadata files as `pathlib.Path` objects.

    :param d: Filename of a directory
    :raises RepositoryError: If `d` is not within a Git repository
    :return: Sequence of root metadata filenames
    :rtype: collections.Iterable[pathlib.Path]

    """

    def hunt(f):
        "Check for root metadata at `f` or recur on sibling folders"
        if f.is_file():
            yield f
        else:
            for d in f.parent.iterdir():
                if d.is_dir() and d.name not in PROJECT_EXCLUDE_DIRS:
                    yield from hunt(d / PROJECT_METADATA_NAME)

    # Walk project hierarchy, and yield metadata filenames
    yield from hunt(locateRepositoryRoot(d) / PROJECT_METADATA_NAME)


@icontract.require(lambda r: isRootMetadata(r))
def yieldLimbMetadata(r):
    """Yield limb metadata files from tree of project plans at `r`

    Walk the folders from `r`, and yield the metadata filenames as
    `pathlib.Path` objects.

    :param r: Filename of a root metadata file
    :raises RepositoryError: If `r` is not within a Git repository
    :raises MissingMetadataError: If a folder without project metadata
       is encountered
    :return: Sequence of limb metadata filenames in depth-first
       pre-order traversal
    :rtype: collections.Iterable[pathlib.Path]

    """

    def visit(d):
        "Check for limb metadata at each child folder and recur"
        for e in d.iterdir():
            if e.is_dir() and e.name not in PROJECT_EXCLUDE_DIRS:
                f = e / PROJECT_METADATA_NAME
                if f.is_file():
                    yield f
                    yield from visit(e)
                else:
                    raise MissingMetadataError(f"Missing metadata file: {f}")

    # Walk project hierarchy and yield metadata filenames
    yield from visit(Path(r).resolve().parent)


@icontract.require(lambda d: Path(d).is_dir())
def validateMetadataForest(d):
    """Validate metadata for forest of project plans

    Walk the folders from `locateRepositoryRoot(d)`, and validate the
    metadata of the project plans.  Validate against
    `getMetadataSchema()` and simple self-consistency constraints.

    :param d: Filename of a directory
    :raises RepositoryError: If `d` is not within a Git repository
    :raises MissingMetadataError: If a folder without project metadata
       is encountered
    :raises SchemaError: If a project metadata file is invalid with
       respect to the metadata schema `getMetadataSchema()`
    :raises ValueError: If a self-consistency constraint is violated

    """

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

    def checkNonRoot(metadata):
        "Enforce todo-state constraints on `metadata` of non-root project"
        todo = metadata["todo"]
        uuid = metadata["uuid"]
        if todo == "ROOT":
            raise ValueError(
                f"Non-root project MUST NOT be in 'ROOT' todo state: {uuid}"
            )

    def checkEntries(metadata):
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

    # Walk project hierarchy and validate project metadata
    uuids = {}
    intervals = intervaltree.IntervalTree()
    schema = getMetadataSchema()
    for r in yieldRootMetadata(d):
        with open(r, "r") as src:
            metadata = yaml.load(src, Loader=NoDatesSafeLoader)
            jsonschema.validate(metadata, schema)
            checkUuid(metadata)
            checkRoot(metadata)
            checkEntries(metadata)
        for l in yieldLimbMetadata(r):
            with open(l, "r") as src:
                metadata = yaml.load(src, Loader=NoDatesSafeLoader)
                jsonschema.validate(metadata, schema)
                checkUuid(metadata)
                checkNonRoot(metadata)
                checkEntries(metadata)


# Local Variables:
# ispell-local-dictionary: "american"
# End:
