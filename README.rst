======
Robant
======

:Precis: Maintain project notes and participate in external work flows
:Authors: Andrew Burrow
:Contact: albcorp@gmail.com
:Copyright: 2021-2023 Andrew Lincoln Burrow

``Robant`` is an early prototype of a tool to maintain project plans.
The objective is to enable text to be the simple and efficient means to
make plans, select tasks, record actions, track effort, and recall past
actions while integrating with external work flows.  The basis is a
simple folder hierarchy that comprises notes in structured text,
metadata in yaml, and resources alongside.  ``Robant`` is the tool to
validate, search, and integrate.

``Robant`` attempts to pare down other approaches to project plans in
structured text.  It shares the logic of keeping personal notes close to
hand for easy processing, but seeks to clarify the relationship to
external tools.  The premise is that we seek autonomy in the
representation of our work, but are increasingly being asked to
collaborate through software systems that impose representations of
work.  ``Robant`` is intended to assist the individual to establish
their own view in the context of signals from external views.

------------
Installation
------------

This prototype uses `Poetry`_ to manage dependencies and build
packages.  Therefore, your first step should be to ensure that Poetry is
available on your workstation.

.. code:: bash

   sudo dnf install poetry

Build the prototype using the ``install`` subcommand.

.. code:: bash

   poetry install

Get help on the prototype using the ``run`` subcommand.

.. code:: bash

   poetry run robant -h

.. _Poetry:
   https://python-poetry.org/

.. Local Variables:
.. mode: rst
.. ispell-local-dictionary: "british"
.. End:
