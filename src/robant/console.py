#! /usr/bin/python

"""Provide command line tool to operate on a project hierarchy

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

"""

__docformat__ = "restructuredtext"


import argparse


def reportUnimplemented(args):
    print("Command not yet implemented")


def run():
    parser = argparse.ArgumentParser(
        prog="robant",
        description=("Operate on a project hierarchy under a state model"),
        epilog=(
            "robant Copyright (C) 2021 Andrew Burrow. "
            "This program comes with ABSOLUTELY NO WARRANTY. "
            "This is free software, and you are welcome to redistribute it "
            "under the conditions set out in the license"
        ),
    )
    subparsers = parser.add_subparsers(
        required=True,
    )

    # Specify global options
    parser.add_argument(
        "-r",
        "--root",
        default=".",
        help="read project hierarchy from DIRECTORY",
        metavar="DIRECTORY",
    )

    # Specify `about` subcommand
    parser_about = subparsers.add_parser(
        "about",
        description="Show information about Robant",
        help="Show information about Robant",
    )
    parser_about.set_defaults(func=reportUnimplemented)

    # Specify `model` subcommand
    parser_model = subparsers.add_parser(
        "model",
        description="Validate the state model and check satisfiability",
        help="Validate the state model and check satisfiability",
    )
    parser_model.set_defaults(func=reportUnimplemented)

    # Specify `validate` subcommand
    parser_validate = subparsers.add_parser(
        "validate",
        description="Validate the project hierarchy against the state model",
        help="Validate the project hierarchy against the state model",
    )
    parser_validate.add_argument(
        "-d",
        "--dir",
        default=".",
        help="validate projects under DIRECTORY",
        metavar="DIRECTORY",
    )
    parser_validate.set_defaults(func=reportUnimplemented)

    # Specify `add` subcommand
    parser_add = subparsers.add_parser(
        "add",
        description="Add new project to the project hierarchy",
        help="Add new project to the project hierarchy",
    )
    parser_add.add_argument(
        "-d",
        "--dir",
        default=".",
        help="create project in DIRECTORY",
        metavar="DIRECTORY",
    )
    parser_add.add_argument(
        "-s",
        "--state",
        required=True,
        help="set project TODO state",
        metavar="TODO",
    )
    parser_add.add_argument(
        "-t",
        "--title",
        required=True,
        help="set project title",
        metavar="TITLE",
    )
    parser_add.set_defaults(func=reportUnimplemented)

    # Parse the arguments.  Call selected function
    args = parser.parse_args()
    args.func(args)


# Local Variables:
# ispell-local-dictionary: "american"
# End:
