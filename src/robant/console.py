#! /usr/bin/python

"""Validate project metadata and folders against schema and self-consistency constraints

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

Read project metadata files and folder structure, and check that metadata
conforms to the project plans schema and satisifies simple self-consistency
constraints

"""

__docformat__ = "restructuredtext"


import argparse

from robant.helpers import validateMetadataForest


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
        "-p",
        "--project",
        action="store",
        default=".",
        help="Filename of project to validate",
    )
    args = parser.parse_args()

    # Validate the project rooted at `PROJECT`
    validateMetadataForest(args.project)


# Local Variables:
# ispell-local-dictionary: "american"
# End:
