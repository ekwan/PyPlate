.. _amount-remaining:

Amount Remaining
------------------

-  In this mode, we can determine the total volume/mass/quantity in a
   given Container before and after a recipe stage
-  If material is added during the specified recipe stage, :ref:`container-flow-tracking` should be used instead
-  This may be used to track the usage of a mixture, rather than a
   single substance


Refer to :ref:`minimal-recipe` document for the recipe being queried in the examples below.

How to use ``get_amount_remaining()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   def get_amount_remaining(container: Container | Plate, timeframe, str='all', unit: str | None = None, mode: str = 'after')

-  ``container``: The container to query
-  ``timeframe``: The timeframe from which to get the volume
-  ``unit``: The unit to return the amount in
-  ``mode``: Whether to query the container before or after the stage

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
