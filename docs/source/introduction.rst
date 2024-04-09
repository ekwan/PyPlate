Introduction
============

The *PyPlate* Python API defines a set of objects and operations for
implementing a high-throughput screen of chemical or biological
conditions. *PyPlate* assists with the enumeration of solid or liquid
handling steps, ensures that those steps are physically reasonable, and
provides plate visualization capabilities.

Scope
"""""

*PyPlate* specifically focuses on the implementation of high-throughput
experimentation (HTE). The upstream process of designing the screens
themselves will be handled elsewhere. Similarly, the downstream process
of analyzing the outcomes of screens will also be handled elsewhere.

External Classes
""""""""""""""""

Four simple HTE classes will be exposed to the user: ``Substance``,
``Container``, ``Plate``, and ``Recipe``. *All classes are immutable.*
(An immutable object is one whose fields cannot be changed once it has
been constructed.)

Quickstart Example, Explained
"""""""""""""""""""""""""""""

::

    from pyplate import Substance, Container, Plate, Recipe

Import the necessary classes from the ``PyPlate`` module.

::

    triethylamine = Substance.liquid(name="triethylamine", mol_weight=101.19, density=0.726)

Create a liquid substance, triethylamine, with a molecular weight of 101.19 g/mol and a density of 0.726 g/mL.

::

    water = Substance.liquid(name="water", mol_weight=18.015, density=1.0)

Create another liquid substance, water, with a molecular weight of 18.015 g/mol and a density of 1.0 g/mL.

::

    triethylamine_50mM = Container.create_solution(name='triethylamine 0.05 M', solute=triethylamine, solvent=water,
                                                   concentration='50 mM', total_quantity='10 mL')

Create a 0.05 M solution of triethylamine in water with a total quantity of 10 mL.

::

    plate = Plate(name='plate', max_volume_per_well='50 uL')

Create a 96-well plate with a maximum volume of 50 uL per well.

::

    recipe = Recipe().uses(triethylamine_50mM, plate)

Declare that the recipe will use the triethylamine_50mM solution and the plate.

::

    recipe.transfer(source=triethylamine_50mM, destination=plate[2:7, 2:11], quantity='10 uL')

Transfer 10 uL of the triethylamine_50mM solution to the wells in the 2nd through 7th rows and the 2nd through 11th columns of the plate.

::

    results = recipe.bake()

Bakes the recipe, ensuring that all the steps are logically consistent and returning the results.
The results are a dictionary with the names of the containers and plates as keys and the final state of the containers as values.

::

    triethylamine_50mM = results[triethylamine_50mM.name]
    plate = results[plate.name]

Retrieve the final state of the triethylamine_50mM solution and the plate from the results.

::

    recipe.visualize(what=plate, mode='final', unit='uL', timeframe='all')

Get a stylized dataframe of the volume in each well of ``plate`` in uL.

.. image:: images/simple_visualization.png
