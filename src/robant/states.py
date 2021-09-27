#! /usr/bin/python

"""Operations on the TODO state model

:Author: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021 Andrew Burrow

"""

__docformat__ = "restructuredtext"


# Standard library modules

from itertools import chain
from json import loads
from pathlib import Path
from pkgutil import get_data
from typing import Generator, Union

import re


# Third party modules

from pydantic import (
    BaseModel,
    DirectoryPath,
    ValidationError,
    constr,
    validate_arguments,
)


# Local modules

from .constants import (
    STATES_BNAME,
    STATE_PAT,
    STATE_RE,
    STATES_SCHEMA_FNAME,
)
from .exceptions import (
    ModelPartitionError,
    ModelSatisfactionError,
    ModelValidityError,
    HierarchyError,
)
from .hierarchy import (
    locateRepositoryRoot,
)
from .yaml import load_yaml


# Singleton for states JSON schema

STATES_SCHEMA_JSON = None


# Type to specify state model

StateStr = constr(regex=STATE_PAT)


class EmptiedState(BaseModel):
    precis: str


class ConstrainedState(BaseModel):
    precis: str
    constraints: dict[
        StateStr, Union[int, tuple[int], tuple[int, int], StateStr]
    ]


class StateModel(BaseModel):
    fname: Path
    action_states: dict[StateStr, EmptiedState]
    limb_states: dict[StateStr, EmptiedState]
    empty_states: dict[StateStr, EmptiedState]
    open_states: dict[StateStr, ConstrainedState]
    shut_states: dict[StateStr, ConstrainedState]


# Types to specify compiled constraints

CompiledCounts = Union[
    tuple[list[StateStr], int],
    tuple[list[StateStr], int, int],
]
CompiledConstraint = tuple[CompiledCounts, ...]
CompiledConstraints = dict[StateStr, CompiledConstraint]


# Type to specify action counts

ActionCounts = tuple[tuple[constr(regex=STATE_PAT), int], ...]


# Functions


@validate_arguments
def getModelSchema() -> dict:
    """Get the JSON schema for state model

    :return: JSON schema for state model

    """
    global STATES_SCHEMA_JSON
    if not STATES_SCHEMA_JSON:
        STATES_SCHEMA_JSON = loads(get_data(__name__, STATES_SCHEMA_FNAME))
    return STATES_SCHEMA_JSON


@validate_arguments
def compileConstraints(model: StateModel) -> CompiledConstraints:
    """Compile TODO state constraints into explicit form

    For each non-limb project state, compute the cardinality constraints on actions as
    integers on the natural number line over equivalence classes of action states.

    :param model: Results of parsing `MODEL.yml`
    :return: Constraints organised into a dictionary that maps project states to cardinality
       constraints.  The cardinality constraints are represented as a list of the tuples of
       one of the two following forms

       `([ACTN_STATE ...], MIN)`
       `([ACTN_STATE ...], MIN, MAX)`

       where

       `[ACTN_STATE ...]`
          Represents the equivalence class of action states to which the cardinality
          constraint applies.  It contains one or more action states.  Each action state is
          unique to a

       `MIN`
          Represents the minimum count of actions with one of the states in the equivalence
          class

       `MAX`
          Represents the optional maximum count of actions with one of the states in the
          equivalence class.  If it is not present, then there is no maximum count

    """

    # Constrain all empty project states to have zero counts of all actions
    C = {
        s: tuple(([a], 0, 0) for a in model.action_states)
        for s in model.empty_states
    }

    # Constrain all non-empty project states according to their descriptions
    for state, desc in chain(
        model.open_states.items(), model.shut_states.items()
    ):
        C_state = []

        # Compile simple constraints
        for a in model.action_states:
            c = desc.constraints[a]
            if isinstance(c, int):
                C_state.append(([a], c, c))
            elif isinstance(c, tuple):
                C_state.append(([a],) + c)

        # Update equivalence classes for all xrefs
        for a in model.action_states:
            c = desc.constraints[a]
            if isinstance(c, str):
                for C_state_i in C_state:
                    if C_state_i[0][0] == c:
                        C_state_i[0].append(a)
                        break

        C[state] = tuple(C_state)

    return C


@validate_arguments
def satisfies(constraint: CompiledConstraint, counts: ActionCounts) -> bool:
    """Do action `counts` satisfy `constraint`?

    Return true if `counts` satisfies `constraint` on every action state.

    :param constraint: List of cardinality constraints on action states
    :param counts: Dictionary of action states and counts

    """
    for actions, *interval in constraint:
        total = sum(n for s, n in counts if s in actions)
        if interval[0] > total:
            return False
        elif len(interval) > 1 and total > interval[1]:
            return False
    return True


@validate_arguments
def classifiers(
    constraints: CompiledConstraints, counts: ActionCounts
) -> list[StateStr]:
    """Return list of project states that are satisfied by `counts`

    :param constraints: Dictionary of project states and lists of cardinality constraints on
       action states as returned by `compileConstraints`
    :param counts: Dictionary of action states and counts
    :return: List of names of project state that are satisfied by `counts`

    """
    return [
        proj_state
        for proj_state, constraint in constraints.items()
        if satisfies(constraint, counts)
    ]


@validate_arguments
def yieldClassifications(
    model: StateModel, constraints: CompiledConstraints
) -> Generator[tuple[StateStr, ActionCounts], None, None]:
    """Yield project-state and action-count tuples reachable from the empty project

    Starting with the empty project, yield an infinite sequence of project-state and
    action-count tuples.  Each new project state represenation is generated from a preceding
    entry by insertion of an action or transition of an action state.  The sequence is
    ordered by the total count of actions in the action-count tuples.

    :param model: Results of parsing `MODEL.yml`
    :param constraints: Dictionary of project states and lists of cardinality constraints on
       action states
    :return: Generator of project-state, action-count tuples in ascending order of total
       counts of actions

    """

    def pushBag(curr_state, succ_bag):
        "Push bag of actions onto the FIFO queue if unseen and classified"
        if succ_bag not in bag_index:
            # Classify the new bag
            succ_states = classifiers(constraints, succ_bag)
            if len(succ_states) == 1:
                succ_state = succ_states[0]
                if succ_state in open_states or curr_state in open_states:
                    # Record the new bag
                    bag_fifo.append(succ_bag)
                    bag_index[succ_bag] = succ_state
            elif len(succ_states) > 1:
                raise ModelSatisfactionError(
                    model.fname,
                    "Action counts satisfy multiple project states {0}: {1}".format(
                        ", ".join(states),
                        succ_bag,
                    ),
                )

    # Gather useful state names from model
    action_states = sorted(model.action_states)
    empty_state, *_ = model.empty_states
    open_states = set(chain(model.empty_states, model.open_states))

    # Perform a breadth first traversal over the directed graph *(V, E)* where: bag of
    # action states *b* is an element of *V* iff a single project state *state(b)* is
    # satisfied by *b*; and pair *(b1, b2)* is an element of *E* iff *b1* can be transformed
    # to *b2* by a single action insertion or action transition, AND either *state(b1)* or
    # *state(b2)* is an open state.  Represent the boundary as a queue of vertices
    # supplemented by an index over the vertices.  Represent a bag as a sorted tuple of
    # action state and count pairs.  Order the queue by bag size.  Represent the index as a
    # map from bags in the queue to the project state satisfied by the bag
    bag_fifo = [tuple((a, 0) for a in action_states)]
    bag_index = {bag_fifo[0]: empty_state}
    while bag_fifo:
        # Yield the oldest classification from the FIFO buffer
        bag = bag_fifo.pop(0)
        state = bag_index.pop(bag)
        yield state, bag

        # Collect the new bags reachable by inserting an action
        new_bag_pos = len(bag_fifo)
        for a in action_states:
            ins_bag = tuple((s, (n + 1) if s == a else n) for s, n in bag)
            pushBag(state, ins_bag)

        # Collect the new bags reachable by transitioning an action
        while new_bag_pos < len(bag_fifo):
            # Collect the new bags reachable by action transition ONLY IF the new
            # classification would be yielded.  Without this check, there is a risk that a
            # classification would be yielded even though the src is unclassifiable
            new_bag = bag_fifo[new_bag_pos]
            new_state = bag_index[new_bag]
            new_bag_pos += 1
            for a_curr, c in new_bag:
                if c > 0:
                    for a_succ in action_states:
                        if a_succ != a_curr:
                            trn_bag = tuple(
                                (
                                    s,
                                    (n - 1)
                                    if s == a_curr
                                    else (n + 1)
                                    if s == a_succ
                                    else n,
                                )
                                for s, n in new_bag
                            )
                            pushBag(new_state, trn_bag)


@validate_arguments
def checkModelPartition(model: StateModel):
    """Check that `model` partions the TODO states

    The state model *partitions* the TODO states if and only if the sets `action_states`,
    `limb_states`, `empty_states`, `open_states`, and `shut_states` are pairwise disjoint.

    :param model: Results of parsing `MODEL.yml`
    :raises ModelPartitionError: If `model` declares the same state name in two sections

    """
    state_to_partition = {}
    for partition in [
        "action_states",
        "limb_states",
        "empty_states",
        "open_states",
        "shut_states",
    ]:
        for state in getattr(model, partition):
            if state in state_to_partition:
                raise ModelPartitionError(
                    model.fname,
                    f"Previously declared state name {state} in {partition}",
                )
            state_to_partition[state] = partition


@validate_arguments
def checkModelValidity(model: StateModel):
    """Check that `model` defines constraints on all action states

    Visit each project state in the `open_states` and `shut_states` declarations of `model`.
    Raise an exception if either an action state is missing from the set of constraints, or
    an unknown action state is present in the set of constraints.  Raise an exception if a
    cross reference to another action state in the constraints cannot be resolved

    :param model: Results of parsing `MODEL.yml`
    :raises ModelValidityError: If an error is found in the constraint specifications

    """
    for proj_state, proj_desc in chain(
        model.open_states.items(),
        model.shut_states.items(),
    ):
        for a in proj_desc.constraints:
            if a not in model.action_states:
                raise ModelValidityError(
                    model.fname,
                    f"Unknown action state {a} in project state {proj_state}",
                )
        for a in model.action_states:
            if a not in proj_desc.constraints:
                raise ModelValidityError(
                    model.fname,
                    f"Unconstrained action state {a} in project state {proj_state}",
                )
        for a, c in proj_desc.constraints.items():
            if isinstance(c, str):
                if c not in model.action_states:
                    raise ModelValidityError(
                        model.fname,
                        f"Unknown target on action state {a} in project state {proj_state}",
                    )
                elif isinstance(proj_desc.constraints[c], str):
                    raise ModelValidityError(
                        model.fname,
                        f"Invalid target on action state {a} in project state {proj_state}",
                    )


@validate_arguments
def checkModelSatisfaction(model: StateModel):
    """Check that `model` can generate all project states

    Prove by breadth-first traversal of the graph

    :param model: Results of parsing `MODEL.yml`
    :raises ModelSatisfactionError: If an project state is found to be unsatisfiable

    """
    constraints = compileConstraints(model)
    state_queue = sorted(
        (sum(m for _, m, *_ in c), s) for s, c in constraints.items()
    )
    for state, counts in yieldClassifications(model, constraints):
        depth = sum(c for _, c in counts)
        if depth == state_queue[0][0]:
            if state_queue.count((depth, state)):
                state_queue.remove((depth, state))
                if not state_queue:
                    return True
        elif depth > state_queue[0][0]:
            unsatisfied_str = ", ".join(s for d, s in state_queue if d < depth)
            raise ModelSatisfactionError(
                model.fname,
                f"Project state(s) {unsatisfied_str} cannot be derived with minimal action counts",
            )


@validate_arguments
def getModel(d: DirectoryPath) -> StateModel:
    """Get the state model from project hierarchy

    :param d: Filename of a directory
    :return: Sequence of pairs of labels and metadata filenames where the labels are one of
       ``LIMB``, or ``LEAF``
    :raises HierarchyError: If `d` is not within a Git repository
    :raises HierarchyError: If model file not found at root of Git repository
    :return: State model

    """
    states_path = locateRepositoryRoot(d) / STATES_BNAME
    if not states_path.is_file():
        raise HierarchyError(
            states_path,
            "Missing state model file",
        )
    with open(states_path, "r") as model_src:
        model_json = load_yaml(model_src)
        return StateModel(fname=states_path, **model_json)
