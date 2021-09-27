#! /usr/bin/python

"""Command line for Robant

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

"""

__docformat__ = "restructuredtext"


# Standard library modules

from argparse import ArgumentParser, Namespace
from pathlib import Path


# Third party modules

from intervaltree import IntervalTree
from jsonschema import validate
from yaml import YAMLError


# Local modules

from .constants import (
    ERROR_WITH_COL,
    ERROR_WITH_FILE,
    ERROR_WITH_LN,
    STATES_BNAME,
)
from .exceptions import (
    HierarchyError,
    ModelPartitionError,
    ModelSatisfactionError,
    ModelValidityError,
    ProjectChronologyError,
    ProjectIdentityError,
    ProjectSatisfactionError,
    ProjectStateError,
)
from .hierarchy import (
    locateRepositoryRoot,
    yieldLabeledProjectFiles,
)
from .projects import (
    ProjectMetadata,
    ProjectPlans,
    checkProjectChronology,
    checkProjectIdentity,
    checkProjectSatisfaction,
    checkProjectState,
    getMetadataSchema,
    yieldActions,
)
from .states import (
    StateModel,
    checkModelPartition,
    checkModelSatisfaction,
    checkModelValidity,
    compileConstraints,
    getModel,
    getModelSchema,
)
from .yaml import load_yaml


# Functions


def reportUnimplemented(args: Namespace):
    """Report unimplemented command"""
    print("Command not yet implemented")


def runAbout(args: Namespace):
    """Print information about Robant"""
    print(__doc__)


def runModel(args: Namespace):
    """Validate state model for project hierarchy at `args.root`

    :param args.root: Filename of a directory

    """
    # Load and validate state model
    try:
        uuids = {}
        schema = getModelSchema()
        model_path = locateRepositoryRoot(args.root) / STATES_BNAME
        if not model_path.is_file():
            raise HierarchyError(
                model_path,
                f"Missing state model file",
            )
        with open(model_path, "r") as model_src:
            model_json = load_yaml(model_src)
            validate(model_json, schema)
            model = StateModel(fname=model_path, **model_json)
            checkModelPartition(model)
            checkModelValidity(model)
            checkModelSatisfaction(model)
            print("OK")
    except HierarchyError as err:
        print(ERROR_WITH_FILE.format(err.file, err.message))
    except ModelPartitionError as err:
        print(ERROR_WITH_FILE.format(err.file, err.message))
    except ModelValidityError as err:
        print(ERROR_WITH_FILE.format(err.file, err.message))
    except ModelSatisfactionError as err:
        print(ERROR_WITH_FILE.format(err.file, err.message))
    except YAMLError as err:
        if hasattr(err, "problem_mark"):
            mark = err.problem_mark
            print(
                ERROR_WITH_COL.format(
                    model_path, mark.line + 1, mark.column + 1, err
                )
            )
        else:
            print(ERROR_WITH_FILE.format(model_path, err))


def runValidate(args: Namespace):
    """Validate project hierarchy at `args.dir`

    Walk the folders from `args.root`.  Validate metadata files against
    schema.  Check uniqueness constraints on UUID.  Check TODO state
    constraints on projects and actions.  Check log record constraints
    on intervals and transitions

    :param args.root: Filename of a directory
    :param args.dir: Filename of a directory

    """

    # Walk project hierarchy and validate projects
    try:
        uuids: dict[UuidStr] = {}
        intervals = IntervalTree()
        schema = getMetadataSchema()
        model = getModel(args.root)
        constraints = compileConstraints(model)
        for label, metadata_path, plans_path in yieldLabeledProjectFiles(
            args.dir
        ):
            with open(metadata_path, "r") as metadata_src:
                metadata_json = load_yaml(metadata_src)
                validate(metadata_json, schema)
                metadata = ProjectMetadata(fname=metadata_path, **metadata_json)
            with open(plans_path, "r") as plans_src:
                plans = ProjectPlans(
                    fname=plans_path, actions=list(yieldActions(plans_src))
                )
            checkProjectState(model, label, metadata, plans)
            checkProjectIdentity(model, uuids, label, metadata)
            checkProjectChronology(model, intervals, metadata)
            checkProjectSatisfaction(constraints, metadata, plans)
    except HierarchyError as err:
        print(ERROR_WITH_FILE.format(err.file, err.message))
    except ProjectStateError as err:
        print(ERROR_WITH_FILE.format(err.file, err.message))
    except ProjectIdentityError as err:
        print(ERROR_WITH_FILE.format(err.file, err.message))
    except ProjectChronologyError as err:
        print(ERROR_WITH_FILE.format(err.file, err.message))
    except ProjectSatisfactionError as err:
        print(ERROR_WITH_FILE.format(err.file, err.message))
    except YAMLError as err:
        if hasattr(err, "problem_mark"):
            mark = err.problem_mark
            print(
                ERROR_WITH_COL.format(
                    metadata_path, mark.line + 1, mark.column + 1, err
                )
            )
        else:
            print(ERROR_WITH_FILE.format(metadata_path, err))


def run():
    parser = ArgumentParser(
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
    parser_about.set_defaults(func=runAbout)

    # Specify `model` subcommand
    parser_model = subparsers.add_parser(
        "model",
        description="Validate the state model and check satisfiability",
        help="Validate the state model and check satisfiability",
    )
    parser_model.set_defaults(func=runModel)

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
    parser_validate.set_defaults(func=runValidate)

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
