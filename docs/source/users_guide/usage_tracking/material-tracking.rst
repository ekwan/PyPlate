.. _intermediate-stage-tracking:

Intermediate Stage Tracking
------------------

-  In this mode, we track the change in the volume/mass/quantity of a
   given Container across a specific timeframe
-  We assume that no additional material is added to the Container
   during the given stage
-  This may be used to track the usage of a mixture, rather than a
   single substance
-  Calculations are performed in volume internally

Refer to :ref:`minimal-recipe` document for the recipe being queried in the examples below.

How to use ``get_amount_remaining()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   def get_amount_remaining(container: Container | Plate, timeframe, str='all', unit: str | None = None)

-  ``container``: The container to query
-  ``timeframe``: The timeframe from which to get the volume
-  ``unit``: The unit to return the amount in

.. _example-calls-1:

Example calls
~~~~~~~~~~~~~~

    How much stock_solution remains after transferring liquids in stage 1?

.. code:: python

   recipe.get_amount_remaining(container=dest_container, timeframe='stage 1', unit='mL')

The volume of ``stock_solution`` at the end of ``Stage 1`` is ``40 mL``


.. toctree::
    :hidden:
    :titlesonly:

    self
