.. role:: style2
    :class: .rst-content h1
Usage Tracking
==============

-  PyPlate offers the ability to see how much of a given Substance or
   mixture has been used
-  Usage may be calculated over the entire recipe, or during a specific recipe stage
-  Three usage tracking modes are offered:

   - :ref:`substance-tracking`: reports how much of a particular Substance has entered specified destination containers
   - :ref:`intermediate-stage-tracking`: reports the the mass/volume/quantity of a particular Container at the end or start of a Stage
   - :ref:`container-flow-tracking`: reports the inflows and outflows of a particular Container, which is useful in the case where materials are added to the container during the recipe stage

.. raw:: html

   <h2>Minimal Examples</h2>


.. raw:: html

    <h4>Example 1:</h4>

Simple example: create a stock solution, and then use it::

   water = Substance.liquid('H2O', mol_weight=18.0153, density=1)
   sodium_sulfate = Substance.solid('Sodium sulfate', 142.04)

   recipe = Recipe()
   container = recipe.create_container('container', initial_contents=None)

   stock_solution = recipe.create_solution(solute=sodium_sulfate, solvent=water, concentration='0.5 M',
                                           total_quantity='50 mL')

   recipe.transfer(stock_solution, container, '10 mL')

   recipe.bake()

::

    >>> recipe.get_substance_used(substance=sodium_sulfate, destinations=[container], unit='mmol')
    5.0


In this call, we use substance tracking to see how much sodium sulfate we've used during the entire recipe. PyPlate compare the contents of ``container`` at the beginning and end of the recipe to find that the net difference
in the amount of sodium sulfate is 5.0 mmol. Thus, we've "used" 5.0 mmol of sodium sulfate.

.. raw:: html

    <h4>Example 2:</h4>

Create a stock solution, use it, then add to it again, and use it again::

       water = Substance.liquid('H2O', mol_weight=18.0153, density=1)
       sodium_sulfate = Substance.solid('Sodium sulfate', 142.04)

       recipe = Recipe()
       container = recipe.create_container('container', initial_contents=None)

       stock_solution = recipe.create_solution(solute=sodium_sulfate, solvent=water, concentration='0.5 M',
                                               total_quantity='50 mL')

       recipe.start_stage('stage 1')
       recipe.transfer(stock_solution, container, '10 mL')

       recipe.dilute(destination=stock_solution, solute=sodium_sulfate, concentration='0.25 M', solvent=water)
       recipe.end_stage('stage 1')

       recipe.transfer(stock_solution, container, '10 mL')

       recipe.bake()

::

    >>> recipe.substance_used(substance=water, destinations=[container], unit='mmol')
    1051.034

In this call, we compare the contents of ``container`` at the beginning and end of the recipe to find that the net difference
in the amount of water is 1051.034 mmol. Thus, we've "used" 1051.034 mmol of water.

    >>> recipe.substance_used(substance=water, destinations=[stock_solution], unit='mmol', timeframe='stage 1')
    1704.673

In this call, we compare the contents of ``stock_solution`` at the beginning and end of the recipe to find that the net difference
in the amount of water is 1051.034 mmol. Thus, we've "used" 1051.034 mmol of water to diluting the solution.

    >>> recipe.get_container_flows(container=stock_solution, unit='mL', timeframe='all')
    {'in': 90.0, 'out': 20.0}

In this call, we track the the additions/removal of materials to/from ``container`` at during the entire recipe to find
that we've added 90 mL of water but only taken 20 mL out.

.. toctree::
    :hidden:
    :maxdepth: 1

    usage_tracking/substance-tracking.rst
    usage_tracking/material-tracking.rst
    usage_tracking/flow-tracking.rst
    usage_tracking/minimal-recipe.rst
