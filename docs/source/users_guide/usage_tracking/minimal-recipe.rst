.. _minimal-recipe:

Minimal Recipe
==============

For the examples in the usage tracking documentation we will consider this recipe:

.. code:: python

   from pyplate import Substance, Recipe, Container

   water = Substance.liquid('H2O', mol_weight=18.0153, density=1)
   sodium_sulfate = Substance.solid('Sodium sulfate', 142.04)

   recipe = Recipe()
   container = recipe.create_container('container', initial_contents=None)

   stock_solution = recipe.create_solution(solute=sodium_sulfate, solvent=water, concentration='0.5 M',
                                           total_quantity='50 mL')

   recipe.start_stage('stage 1')
   recipe.transfer(stock_solution, container, '10 mL')
   recipe.end_stage('stage 1')

   recipe.start_stage('stage 2')
   recipe.remove(container, water)

   # implicit end of stage at end of recipe
   recipe.end_stage('stage 2')

   recipe.bake()

-  The “all” stage begins at the start of the recipe and lasts until the
   end of the recipe
-  A stage can be started with ``recipe.start_stage`` and it keeps track
   of steps that are performed until ``recipe.end_stage`` is called or
   the end of the recipe, whichever comes first
-  Because stage 2 ends with the end of the recipe in the example above,
   ``recipe.end_stage('stage 2')`` is redundant

.. toctree::
    :hidden:
    :titlesonly:

    self
