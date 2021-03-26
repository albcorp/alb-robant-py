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

import icontract
import yaml


# Filenames of JSON schema

METADATA_SCHEMA_FNAME = "schema/metadata.json"


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

    # Read metadata schema as text
    metadata_schema = json.loads(pkgutil.get_data(__name__, METADATA_SCHEMA_FNAME))
    print(f"schema:\n{metadata_schema}")


# Local Variables:
# ispell-local-dictionary: "american"
# End:
