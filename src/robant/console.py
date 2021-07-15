#! /usr/bin/python

"""Validate project metadata against schema and TODO state constraints

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

"""

__docformat__ = "restructuredtext"


import argparse

from robant.helpers import validateMetadataForest


def run_validation():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="robant",
        description=(
            "Walk project hierarchy reading the metadata and project plan files. "
            "Validate 'METADATA.yml' files against schema. Check uniqueness "
            "constraints on project UUIDs. Check TODO state constraints on projects "
            "and actions. Check log record constraints on intervals and transitions"
        ),
        epilog=(
            "robant Copyright (C) 2021 Andrew Burrow. "
            "This program comes with ABSOLUTELY NO WARRANTY. "
            "This is free software, and you are welcome to redistribute it "
            "under the conditions set out in the license"
        ),
    )
    parser.add_argument(
        "-p",
        "--project",
        action="store",
        default=".",
        help="Filename of folder containing project plans to validate",
    )
    args = parser.parse_args()

    # Validate the project rooted at `PROJECT`
    validateMetadataForest(args.project)


# Local Variables:
# ispell-local-dictionary: "american"
# End:
