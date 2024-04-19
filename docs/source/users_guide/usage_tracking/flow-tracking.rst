.. _container-flow-tracking:

Container Flow Tracking
-----------------------

-  In this tracking mode, we track the volume flowing in and out of a
   given Container during a specific timeframe
-  This may be used to track the usage of a solution, rather than a
   single substance
-  Timeframes are specified using recipe stages as in substance-level
   tracking

Refer to :ref:`minimal-recipe` document for the recipe being queried in the examples below.

How to use ``get_container_flows()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   def get_container_flows(container: Container | Plate, timeframe: str = 'all', unit='uL': str | None = None)

-  ``container``: The container to get flows for
-  ``timeframe``: The timeframe over which the deltas of the
   destinations should be compared
-  ``unit``: The unit to return flows in

.. _example-calls-2:

Example calls
~~~~~~~~~~~~~~

   What are the flows for ``stock_solution`` across the entire recipe?

.. code:: python

   recipe.get_container_flows(container=stock_solution, timeframe='all', unit='mL')

We take the difference of the flows of ``stock_solution`` at the
beginning and end of the recipe and return the dictionary. The
difference of the outflows is ``10 mL`` and the difference of the
inflows is ``50 mL``.

This returns: ``{"in": 50, "out": 10}``

   What are the flows for ``dest_container`` across ``Stage 2``?

.. code:: python

   recipe.get_container_flows(container=dest_container, timeframe='stage 2', unit='mL')

-  We take the difference of the flows of ``dest_container`` at the
   beginning and end of the recipe and return the dictionary. The
   difference of the outflows is ``9.279 mL`` and the difference of the
   inflows is ``0 mL``.

.. _recipe-walkthrough-2:

Recipe Walkthrough
~~~~~~~~~~~~~~~~~~

.. _start-of-recipe-1:

Start of Recipe:
^^^^^^^^^^^^^^^^

.. code:: python

   container: {in: "0 mL", out: "0 mL"}
   stock_solution: {in: "0 mL", out: "0 mL"}

.. _stage-1-start-1:

Stage 1 (start):
^^^^^^^^^^^^^^^^

Flows of containers at the start of Stage 1:

.. code:: python

   dest_container: {in: "0 mL", out: "0 mL"}
   stock_solution: {in: "50 mL", out: "0 mL"}

.. _stage-1-end-1:

Stage 1 (end):
^^^^^^^^^^^^^^

Contents of containers at the end of Stage 1:

.. code:: python

   dest_container: {in: "10 mL", out: "0 mL"}
   stock_solution: {in: "50 mL", out: "10 mL"}

.. _stage-2-start-2:

Stage 2 (start):
^^^^^^^^^^^^^^^^

Contents of containers at the beginning of Stage 2:

.. code:: python

   dest_container: {in: "10 mL", out: "0 mL"}
   stock_solution: {in: "50 mL", out: "10 mL"}

.. _stage-2-end-2:

Stage 2 (end):
^^^^^^^^^^^^^^

Contents of containers at the end of Stage 2:

.. code:: python

   dest_container: {in: "10 mL", out: "9.2779 mL"}
   stock_solution: {in: "50 mL", out: "10 mL"}


.. toctree::
    :hidden:
    :titlesonly:

    self