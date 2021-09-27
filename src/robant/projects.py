#! /usr/bin/python

"""Operations on projects

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

"""

__docformat__ = "restructuredtext"


# Standard library modules

from datetime import datetime
from json import loads
from pathlib import Path
from pkgutil import get_data
from typing import Generator, Optional, TextIO, Union


# Third party modules

from intervaltree import IntervalTree
from pydantic import (
    BaseModel,
    DirectoryPath,
    Field,
    FilePath,
    ValidationError,
    constr,
    validate_arguments,
)


# Local modules

from .constants import (
    ACTION_RE,
    METADATA_SCHEMA_FNAME,
    SLUG_PAT,
    TAG_PAT,
    UUID_PAT,
)
from .exceptions import (
    HierarchyError,
    ProjectChronologyError,
    ProjectIdentityError,
    ProjectSatisfactionError,
    ProjectStateError,
)
from .hierarchy import (
    LabelStr,
    locateRepositoryRoot,
)
from .states import (
    CompiledConstraints,
    StateModel,
    StateStr,
)


# Singleton for metadata JSON schema

METADATA_SCHEMA_JSON = None


# Types to specify projects

UuidStr = constr(regex=UUID_PAT)
SlugStr = constr(regex=SLUG_PAT)
TagStr = constr(regex=TAG_PAT)


class GitHubIssue(BaseModel):
    repo: str
    issue: int


class GitHubEvent(BaseModel):
    event: int


class TransitionEntry(BaseModel):
    at: datetime
    to_state: StateStr = Field(alias="to")
    from_state: Optional[StateStr] = Field(alias="from")
    github: Optional[GitHubEvent]
    note: Optional[str]


class IntervalEntry(BaseModel):
    start: datetime
    stop: datetime
    note: Optional[str]


class ProjectMetadata(BaseModel):
    fname: Path
    uuid: UuidStr
    slug: SlugStr
    title: str
    todo: StateStr
    tags: list[TagStr]
    github: Optional[GitHubIssue]
    logbook: list[Union[TransitionEntry, IntervalEntry]]


class ProjectPlans(BaseModel):
    fname: Path
    actions: list[tuple[int, StateStr, str]]


# Functions


@validate_arguments
def getMetadataSchema() -> dict:
    """Get the JSON schema for project metadata

    :return: JSON schema for project plan metadata
    :rtype: dict

    """
    global METADATA_SCHEMA_JSON
    if not METADATA_SCHEMA_JSON:
        METADATA_SCHEMA_JSON = loads(get_data(__name__, METADATA_SCHEMA_FNAME))
    return METADATA_SCHEMA_JSON


def yieldActions(
    plans_src: TextIO,
) -> Generator[tuple[int, StateStr, str], None, None]:
    "Yield actions from `plans_src` as (line number, TODO state, title) tuples"
    for line, text in enumerate(plans_src, 1):
        action_match = ACTION_RE.match(text)
        if action_match:
            yield (line, action_match["todo"], action_match["title"])


@validate_arguments
def checkProjectState(
    model: StateModel,
    label: LabelStr,
    metadata: ProjectMetadata,
    plans: ProjectPlans,
):
    """Check TODO states of project described by `metadata` and `plans`

    :param model: State model of project hierarchy
    :param label: Structural classification of project in hierarchy as
       either ``LIMB`` or ``LEAF``
    :param metadata: Project metadata
    :param plans: Actions from project plans
    :raises ProjectStateError: If project TODO state in `metadata` is
       not in `model`
    :raises ProjectStateError: If `label is ``LIMB`` and project TODO
       state is not a limb project state
    :raises ProjectStateError: If action TODO state in `plans` is not in
       `model`

    """
    project_states = set().union(
        model.limb_states,
        model.empty_states,
        model.open_states,
        model.shut_states,
    )

    # Enforce valid project todo state
    if metadata.todo not in project_states:
        raise ProjectStateError(
            metadata.fname,
            f"Unknown project TODO state: {metadata.todo}",
        )
    if label == "LIMB" and metadata.todo not in model.limb_states:
        raise ProjectStateError(
            metadata.fname,
            f"Invalid project TODO state for limb project: {metadata.todo}",
        )

    # Enforce valid project todo states in logbook
    for curr in filter(
        lambda e: isinstance(e, TransitionEntry), metadata.logbook
    ):
        if curr.to_state not in project_states:
            raise ProjectStateError(
                metadata.fname,
                f"Unknown project TODO state in logbook entry: {curr.to_state}: {curr.at}",
            )
        elif curr.from_state and curr.from_state not in project_states:
            raise ProjectStateError(
                metadata.fname,
                f"Unknown project TODO state in logbook entry: {curr.from_state}: {curr.at}",
            )

    # Enforce valid action todo states in project plans
    for line, todo, title in plans.actions:
        if todo not in model.action_states:
            raise ProjectStateError(
                plans.fname,
                f"Unknown action TODO state: {todo}",
            )


@validate_arguments
def checkProjectIdentity(
    model: StateModel,
    uuids: dict[UuidStr, FilePath],
    label: LabelStr,
    metadata: ProjectMetadata,
):
    """Check IDs of project described by `metadata`

    :param model: State model of project hierarchy
    :param uuids: Map of project UUID values to corresponding project metadata filenames.
       Updated by this function
    :param label: Structural classification of project in hierarchy as either ``LIMB`` or
       ``LEAF``
    :param metadata: Project metadata
    :raises ProjectIdentityError: If UUID in `metadata` is already present in `uuids`
    :raises ProjectIdentityError: If slug in `metadata` does not match folder name from
       `fname` in `metadata` AND todo state in `metadata` is not a limb state

    """
    # Enforce uniqueness constraint
    if metadata.uuid in uuids:
        raise ProjectIdentityError(
            fname,
            "Project UUID MUST be unique: {0}: {1}".format(
                metadata.uuid, uuids[metadata.uuid]
            ),
        )
    else:
        uuids[metadata.uuid] = metadata.fname

    # Enforce structural constraints
    if (
        metadata.slug != metadata.fname.parent.name
        and metadata.todo not in model.limb_states
    ):
        raise ProjectIdentityError(
            metadata.fname,
            f"Project slug MUST match folder name: {metadata.slug}",
        )


@validate_arguments(config=dict(arbitrary_types_allowed=True))
def checkProjectChronology(
    model: StateModel,
    intervals: IntervalTree,
    metadata: ProjectMetadata,
):
    """Check chronology of project described by `metadata`

    :param model: State model of project hierarchy
    :param label: Structural classification of project in hierarchy as either ``LIMB`` or
       ``LEAF``
    :param metadata: Project metadata
    :param actions: Project actions
    :raises ProjectStateError: If project TODO state in `metadata` is not in `model`
    :raises ProjectStateError: If `label is ``LIMB`` and project TODO state is not a limb
       project state
    :raises ProjectStateError: If action TODO state in `actions` is not in `model`

    :param model: State model of project hierarchy
    :param intervals: Interval tree of time intervals in projects processed at this point
       where each interval is mapped to the filename of the project metadata where it was
       recorded.  Updated by thisfunction
    :param metadata: Project metadata
    :raises ProjectChronologyError: If negative time interval found in `metadata`
    :raises ProjectChronologyError: If time interval in `metadata` overlaps any in `intervals`
    :raises ProjectChronologyError: If first logbook entry does not record the time of
       project inception and intial project state
    :raises ProjectChronologyError: If project is in limb state and records effort or a
       state transition
    :raises ProjectChronologyError: If a logbook entry starts before the preceding entry
       stops
    :raises ProjectChronologyError: If a logbook transition does not agree with the
       preceding transition
    :raises ProjectChronologyError: If a logbook interval records effort against a limb
       project state or shut project state
    :raises ProjectChronologyError: If a final logbook transition does not agree with the
       project state

    """
    # Enforce interval constraints on logbook entries
    for curr in filter(
        lambda e: isinstance(e, IntervalEntry), metadata.logbook
    ):
        if curr.stop < curr.start:
            raise ProjectChronologyError(
                metadata.fname,
                f"Logbook time intervals MUST be non-negative: {curr.start}, {curr.stop}",
            )
        elif intervals[curr.start : curr.stop]:
            olap = next(iter(intervals[curr.start : curr.stop]))
            olap_start = max(curr.start, olap[0])
            olap_stop = min(curr.stop, olap[1])
            raise ProjectChronologyError(
                metadata.fname,
                f"Logbook time intervals MUST NOT overlap: {olap_start}, {olap_stop}",
            )
        else:
            intervals[curr.start : curr.stop] = metadata.fname

    # Enforce record of project inception
    if (
        not isinstance(metadata.logbook[-1], TransitionEntry)
        or metadata.logbook[-1].from_state
    ):
        raise ProjectChronologyError(
            metadata.fname,
            f"Logbook MUST record project inception",
        )

    # Enforce leaf effort constraint
    if metadata.todo in model.limb_states and len(metadata.logbook) > 1:
        raise ProjectChronologyError(
            metadata.fname,
            f"Limb projects MUST NOT record activity",
        )

    # Enforce sequence constraints on logbook entries, project state continuity on
    # transition entries, effort restrictions on limb and shut states, and agreement between
    # project todo state and finaly transition entry
    pred_state = metadata.logbook[-1].to_state
    pred_stop = metadata.logbook[-1].at
    for curr in metadata.logbook[-2::-1]:
        if isinstance(curr, TransitionEntry):
            if curr.at < pred_stop:
                raise ProjectChronologyError(
                    metadata.fname,
                    f"Logbook entry MUST NOT start before preceding entry: {curr.at}",
                )
            if curr.from_state != pred_state:
                raise ProjectChronologyError(
                    metadata.fname,
                    f"Logbook transition MUST record preceding state: {curr.at}",
                )
            pred_state = curr.to_state
            pred_stop = curr.at
        else:
            if curr.start < pred_stop:
                raise ProjectChronologyError(
                    metadata.fname,
                    f"Logbook entry MUST NOT start before preceding entry: {curr.start}",
                )
            if pred_state in model.limb_states:
                raise ProjectChronologyError(
                    metadata.fname,
                    f"Effort MUST NOT be recorded against limb project state: {pred_state}: {curr.start}",
                )
            if pred_state in model.shut_states:
                raise ProjectChronologyError(
                    metadata.fname,
                    f"Effort MUST NOT be recorded against shut project state: {pred_state}: {curr.start}",
                )
            pred_stop = curr.stop
    if pred_state != metadata.todo:
        raise ProjectChronologyError(
            metadata.fname,
            f"Final logbook transition MUST match project state: {pred_state}",
        )


@validate_arguments
def checkProjectSatisfaction(
    constraints: CompiledConstraints,
    metadata: ProjectMetadata,
    plans: ProjectPlans,
):
    """Check satisfaction of TODO states of project described by `metadata` and `actions`

    :param constraints: Compiled TODO state constraints from state model
    :param metadata: Project metadata
    :param actions: Project actions
    :raises ProjectSatisfactionError: If actions recorded against limb project
    :raises ProjectSatisfactionError: If lower bound on action states not reached
    :raises ProjectSatisfactionError: If upper bound on actions states exceeded

    """
    if metadata.todo not in constraints:
        for line, state, title in plans.actions:
            raise ProjectSatisfactionError(
                metadata.fname,
                f"Actions MUST NOT be recorded against limb project state: {metadata.todo}: {state} {title}",
            )
    else:
        for states, *interval in constraints[metadata.todo]:
            count = 0
            min_count = interval[0]
            if len(interval) == 1:
                for line, state, title in plans.actions:
                    if state in states:
                        count += 1
                        if count == min_count:
                            break
            else:
                max_count = interval[1]
                for line, state, title in plans.actions:
                    if state in states:
                        count += 1
                        if count > max_count:
                            states_str = " + ".join(states)
                            raise ProjectSatisfactionError(
                                metadata.fname,
                                f"Upper bound on actions states exceeded: {metadata.todo}: {min_count} <= {states_str} <= {max_count}",
                            )
            if count < min_count:
                states_str = " + ".join(states)
                raise ProjectSatisfactionError(
                    metadata.fname,
                    f"Lower bound on action states not reached: {metadata.todo}: {min_count} <= {states_str}",
                )


# Local Variables:
# ispell-local-dictionary: "american"
# End:
