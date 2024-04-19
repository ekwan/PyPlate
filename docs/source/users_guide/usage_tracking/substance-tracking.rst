.. _substance-tracking:

Substance Tracking
------------------------

-  Substance tracking reports how much of a particular Substance has been used
-  Usage is defined as the net increase of the amount of a given
   Substance in a destination set of Containers or Plates during a specified timeframe
-  When calling ``recipe.remove``, the Substance is considered to be
   moved to a special trash container, which is always considered a
   destination
-  If no destinations set is explicitly specified, the set of all Plates is considered to be the destination
-  If the amount of the substance in the destinations undergoes a net
   decrease during the timeframe, an error is thrown

Refer to :ref:`minimal-recipe` document for the recipe being queried in the examples below.

How to use ``substance_used()``:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   def substance_used(self, substance: Substance, timeframe: str = 'all', unit: str = None,
                   destinations: Iterable[Container | Plate] | str = "plates")

-  ``substance``: The Substance to track
-  ``timeframe``: The timeframe over which the net difference should be
   calculated
-  ``unit``: The unit to return usage in
-  ``destinations``: A list of ``Containers`` and/or ``Plates`` to be
   considered destinations. Alternatively, pass in ``"plates"`` to
   consider all plates to be destinations. By default, all plates are
   considered destinations.
-  Default units for substances are determined by their type:

   -  solids: ``g``
   -  liquids: ``mL``
   -  enzyme: ``U``

Example calls
~~~~~~~~~~~~~~

   How much sodium sulfate was used during the whole recipe if
   ``container`` is our only destination?


>>> recipe.substance_used(substance=sodium_sulfate, timeframe='all', unit='mmol', destinations=[container])
5.0

-  We compare the amount of ``sodium_sulfate`` in ``container`` at the beginning and end of the recipe
-  There are ``0 mmol`` at the beginning and ``5 mmol`` at the end
-  The net difference for ``container`` is ``5 mmol``, which is our “amount used”


    How much water was used during the whole recipe if ``container`` is
    our only destination?



>>> recipe.substance_used(substance=water, timeframe='all', unit='mmol', destinations=[container])
515.0

-  We compare the amount of water in ``container`` at the beginning and end of the recipe
-  There are ``0 mmol`` of water in ``container`` at the beginning of the recipe and ``0 mmol`` of water in ``container`` at the end of the recipe
-  The net difference for ``container`` is ``0 mmol``.
-  However, trash is always an implicit destination that stores removed substances.
-  The amount of water in ``trash`` increases by ``515 mmol`` during the recipe
-  Thus, we sum the two amounts and return ``515 mmol``

    How much sodium sulfate was used during ``Stage 1``\ if
    ``stock_solution`` is our only destination?

>>> recipe.substance_used(substance=sodium_sulfate, timeframe='Stage 1', unit='mmol', destinations=[stock_container])
ValueError: Substance tracking assumes a net increase in the amount of the substance being tracked in the destination set.
The amount of sodium_sulfate in the destinations decreased by 5 mmol.


-  We compare the amount of sodium sulfate in ``stock_solution`` at the beginning and end of ``Stage 1``
-  During this during stage 1 we transfer ``10 ml`` from ``stock_solution`` to ``container``
-  But since ``stock_solution`` is specified as a destination, and there is a net decrease of ``5 mmol`` of sodium sulfate
-  Logically, it would make sense for ``stock_solution`` to be considered a source and not a destination
-  Thus, ``amount_used`` throws an error

Recipe Walkthrough
~~~~~~~~~~~~~~~~~~

The contents of all containers in the example recipe during different
timeframes are shown below:

Start of Recipe:
^^^^^^^^^^^^^^^^
::

    container: {water: "0 mmol", sodium_sulfate: "0 mmol"}
    stock_solution: {water: "0 mmol", sodium_sulfate: "0 mmol"}
    trash: {water: "0 mmol", sodium_sulfate: "0 mmol"}``

Stage 1 (start):
^^^^^^^^^^^^^^^^
::

    container: {water: "2578 mmol", sodium_sulfate: "25 mmol"}
    stock_solution: {water: "0 mmol", sodium_sulfate: "0 mmol"}
    trash: {water: "0 mmol", sodium_sulfate: "0 mmol"}``

Stage 1 (end):
^^^^^^^^^^^^^^^^
::

    stock_solution: {water: "2063 mmol", sodium_sulfate: "20 mmol"}
    container: {water: "515 mmol", sodium_sulfate: "5 mmol"}
    trash: {water: "0 mmol", sodium_sulfate: "0 mmol"}``

Stage 2 (start):
^^^^^^^^^^^^^^^^
::

    stock_solution: {water: "2063 mmol", sodium_sulfate: "20 mmol"}
    container: {water: "515 mmol", sodium_sulfate: "5 mmol"}
    trash: {water: "0 mmol", sodium_sulfate: "0 mmol"}

Stage 2 (end):
^^^^^^^^^^^^^^
::

    stock_solution: {water: "2063 mmol", sodium_sulfate: "20 mmol"}
    container: {water: "0 mmol", sodium_sulfate: "5 mmol"}
    trash: {water: "515 mmol", sodium_sulfate: "0 mmol"}

.. toctree::
    :hidden:
    :titlesonly:

    self
