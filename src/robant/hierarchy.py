#! /usr/bin/python

"""Operations on the project hierarchy

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

"""

__docformat__ = "restructuredtext"


# Standard library modules

from typing import Generator
from pathlib import Path


# Third party modules

from pydantic import (
    DirectoryPath,
    FilePath,
    constr,
    validate_arguments,
)


# Local modules

from .constants import (
    EXCLUDE_DIRS,
    LABEL_PAT,
    METADATA_BNAME,
    PLANS_BNAME,
    VCS_BNAME,
)
from .exceptions import HierarchyError
from .yaml import load_yaml


# Types to specify position labels in project hierarchy

LabelStr = constr(regex=LABEL_PAT)


# Functions


@validate_arguments
def locateRepositoryRoot(d: Path) -> Path:
    """Search upward from `d` for Git repository root

    :param d: Filename of a directory
    :raises HierarchyError: If `d` is not within a Git repository
    :return: Filename of Git repository root

    """
    for e in (Path(d).resolve() / METADATA_BNAME).parents:
        if (e / VCS_BNAME).is_dir():
            return e
    raise HierarchyError(
        d,
        f"No repository found",
    )


@validate_arguments
def yieldLabeledProjectFiles(
    d: DirectoryPath,
) -> Generator[tuple[LabelStr, FilePath, FilePath], None, None]:
    """Yield metadata and plan files from project hierarchy with position labels

    Walk the folders from `d`, and yield the projects and their place in the project
    hierarchy

    :param d: Filename of a directory
    :raises HierarchyError: If project metadata or plans files not found
    :return: Sequence of triples of the form `(LABEL, METADATA, PLANS)` where

        `LABEL`
           Whether the project is a ``LIMB`` or ``LEAF`` in the project hierarchy

        `METADATA`
           The filename of the metadata file that defines the project

        `PLANS`
           The filename of the plans file that describes the project actions

    """

    def isProject(m: Path, p: Path) -> bool:
        "Do `m` and `p` identify a project folder?"
        if m.is_file() and p.is_file():
            return True
        elif m.is_file():
            raise HierarchyError(
                p,
                "Missing project plans file",
            )
        elif p.is_file():
            raise HierarchyError(
                m,
                "Missing project metadata file",
            )
        else:
            return False

    def hunt(d: Path) -> Generator[tuple[LabelStr, Path], None, None]:
        "Check for limb metadata at `f` and recur on subfolders"
        m = d / METADATA_BNAME
        p = d / PLANS_BNAME
        if isProject(m, p):
            yield "LIMB", m, p
            for e in d.iterdir():
                if e.is_dir() and e.name not in EXCLUDE_DIRS:
                    yield from visit(e)
        else:
            for e in d.iterdir():
                if e.is_dir() and e.name not in EXCLUDE_DIRS:
                    yield from hunt(e)

    def visit(d: Path) -> Generator[tuple[LabelStr, Path], None, None]:
        "Check for limb or leaf metadata and recur on subfolders"
        m = d / METADATA_BNAME
        p = d / PLANS_BNAME
        if isProject(m, p):
            # Defer the yield until a child has been seen
            deferred = True
            for e in d.iterdir():
                if e.is_dir() and e.name not in EXCLUDE_DIRS:
                    if deferred:
                        yield "LIMB", m, p
                        deferred = False
                    yield from visit(e)
            if deferred:
                yield "LEAF", m, p
                deferred = False
        else:
            raise HierarchyError(
                d,
                "Unexpected folder in project hierarchy",
            )

    # Walk project hierarchy, and yield labelled metadata filenames
    d = Path(d).resolve()
    m = d / METADATA_BNAME
    p = d / PLANS_BNAME
    if not isProject(m, p):
        yield from hunt(d)
    else:
        g = d / VCS_BNAME
        n = d.parent / METADATA_BNAME
        q = d.parent / PLANS_BNAME
        if g.is_dir() or not isProject(n, q):
            yield from hunt(d)
        else:
            yield from visit(d)
