#! /usr/bin/python

"""Demonstrate the packaging of a script

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

This code is a simple example of the layout and documentation of python
script

"""

__docformat__ = "restructuredtext"


import argparse


def run():

    parser = argparse.ArgumentParser(
        prog="robant",
        description="Demonstrate a robant script",
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
        action="store_const",
        const=True,
        default=False,
        dest="verbose",
        help="Verbose output",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_const",
        const=True,
        default=False,
        dest="dry_run",
        help="Make no changes",
    )

    args = parser.parse_args()

    if args.verbose:
        print("Verbose output is selected")
    if args.dry_run:
        print("Dry run is selected")
    print("Finished")


# Local Variables:
# ispell-local-dictionary: "american"
# End:
