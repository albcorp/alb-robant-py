#! /usr/bin/python

"""Validate project metadata against schema and TODO state constraints

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

Walk project hierarchy reading files that contain project metadata and
plans, and check that metadata conforms to the schema and satisifies the
TODO state constraints

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
            "TODO state constraints"
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
