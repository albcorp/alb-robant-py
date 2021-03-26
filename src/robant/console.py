#! /usr/bin/python

"""Validate project metadata and folders against schema and self-consistency constraints

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

Read project metadata files and folder structure, and check that
metadata conforms to the project plans schema and satisifies simple
self-consistency constraints

"""

__docformat__ = "restructuredtext"


import argparse
import json
import pkgutil
from pathlib import Path

import icontract
import intervaltree
import jsonschema
import yaml


# Filenames of JSON schema

METADATA_SCHEMA_FNAME = "schema/metadata.json"


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
                (tag, regexp) for tag, regexp in mappings if tag != tag_to_remove
            ]


# Load datetimes as strings to prevent problems when serialising as JSON
NoDatesSafeLoader.remove_implicit_resolver("tag:yaml.org,2002:timestamp")


def isValidSchema(s):
    "Return True only if `s` is a valid draft 4 JSON schema"
    try:
        jsonschema.Draft4Validator.check_schema(s)
        return True
    except:
        return False


@icontract.require(lambda r, s: Path(r).is_dir() and isValidSchema(s))
def validateProjectMetadata(r, s):
    """Validate metadata for forest of project plans reachable from `r`

    Let `r` be a filename of a directory; and let `s` be a JSON schema.  Walk the folders
    from `r`, and validate the metadata of the project plans.  Validate against schema `s`
    and simple self-consistency constraints.  Raise `SchemaError` or `ValueError` for first
    problem detected in values of each

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
            raise ValueError(f"Root project MUST be in 'ROOT' todo state: {uuid}: {todo}")

    def checkNonRoot(metadata):
        "Enforce todo-state constraints on `metadata` of non-root project"
        todo = metadata["todo"]
        uuid = metadata["uuid"]
        if todo == "ROOT":
            raise ValueError(f"Non-root project MUST NOT be in 'ROOT' todo state: {uuid}")

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
                raise ValueError(f"First entry MUST record project inception: {uuid}")
        for pred, curr in zip(logbook[-1::-1], logbook[-2::-1]):
            pred_stop = pred["stop"] if "stop" in pred else pred["at"]
            curr_start = curr["start"] if "start" in curr else curr["at"]
            if curr_start < pred_stop:
                raise ValueError(
                    f"Entry MUST NOT start before preceding entry: {uuid}: {curr_start}"
                )

    def hunt(p):
        "Check for project root at `p` and recur on children"
        if p.is_file():
            try:
                with open(p, "r") as src:
                    metadata = yaml.load(src, Loader=NoDatesSafeLoader)
                    jsonschema.validate(metadata, s)
                    checkUuid(metadata)
                    checkRoot(metadata)
                    checkEntries(metadata)
            except Exception as err:
                print("\n\nFailed validation: {0}: {1}".format(p, err))
            for d in p.parent.iterdir():
                if d.is_dir() and d.name not in ["LIB", "SRC", "TMP"]:
                    visit(d / "METADATA.yml")
        else:
            for d in p.parent.iterdir():
                if d.is_dir() and d.name not in ["LIB", "SRC", "TMP"]:
                    hunt(d / "METADATA.yml")

    def visit(p):
        "Check for project at `p` and recur on children"
        if p.is_file():
            try:
                with open(p, "r") as src:
                    metadata = yaml.load(src, Loader=NoDatesSafeLoader)
                    jsonschema.validate(metadata, s)
                    checkUuid(metadata)
                    checkNonRoot(metadata)
                    checkEntries(metadata)
            except Exception as err:
                print("\n\nFailed validation: {0}: {1}".format(p, err))
        for d in p.parent.iterdir():
            if d.is_dir() and d.name not in ["LIB", "SRC", "TMP"]:
                visit(d / "METADATA.yml")

    # Walk project hierarchy and validate project metadata
    uuids = {}
    intervals = intervaltree.IntervalTree()
    hunt(Path(r).resolve() / "METADATA.yml")


def run_validation():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="robant",
        description=(
            "Validate project metadata and folders against schema and "
            "self-consistency constraints"
        ),
        epilog=(
            "robant Copyright (C) 2021 Andrew Burrow. "
            "This program comes with ABSOLUTELY NO WARRANTY. "
            "This is free software, and you are welcome to redistribute it "
            "under the conditions set out in the license"
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "-p",
        "--project",
        action="store",
        default=".",
        help="Filename of project to validate",
    )
    args = parser.parse_args()

    # Report command line arguments
    if args.verbose:
        print("Verbose output is selected")
    if args.project != ".":
        print(f"Project filename is {args.project}")

    # Parse metadata schema
    metadata_schema = json.loads(pkgutil.get_data(__name__, METADATA_SCHEMA_FNAME))

    # Validate the project rooted at `PROJECT`
    validateProjectMetadata(args.project, metadata_schema)


# Local Variables:
# ispell-local-dictionary: "american"
# End:
