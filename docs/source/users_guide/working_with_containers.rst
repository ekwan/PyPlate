.. _working_with_containers:

Working with Containers
=======================

The following examples use these ``Substance``\ s:

::

    salt = Substance.solid(name='NaCl', mol_weight=58.44)
    water = Substance.liquid(name='H2O', mol_weight=18.01528, density=1.0)
    sodium_sulfate = Substance.solid(name='sodium_sulfate', mol_weight=142.04)
    triethylamine = Substance.liquid(name='triethylamine', mol_weight=101.19, density=0.726)


Creating solutions
""""""""""""""""""

Create a 1 M solution of salt water::

    salt_water = Container.create_solution(solute=salt, solvent=water, concentration='1 mol/L', total_quantity='100 mL')


.. Rework create_solution so concentration='1 g/mL' works.


Getting properties
------------------

You can get the instructions for preparing a ``Container``:

>>> print(salt_water.instructions)
Add 5.844 g of NaCl, 94.156 mL of H2O to a container.

You can get the current concentration of a ``Container`` with respect to a solute:

>>> print(salt_water.get_concentration(solute=salt, units='M'))
1.0

You can get the current volume of a ``Container``:

>>> print(salt_water.get_volume(unit='mL'))
100.0

.. note:: All ``Container``\ s are immutable. Any operations on a ``Container`` will return a new, modified ``Container`` object.

Diluting solutions
""""""""""""""""""

Using the result of the previous example, we can dilute the solution to 0.5 M::

    salt_water = salt_water.dilute(solute=salt, solvent=water, concentration='0.5 M')

>>> print(salt_water.instructions)
Add 5.844 g of NaCl, 94.156 mL of H2O to a container.
Dilute with 100.0 mL of H2O.

>>> print(salt_water.get_volume(unit='mL'))
200.0

>>> print(salt_water.get_concentration(solute=salt, units='M'))
0.5

Filling Containers
""""""""""""""""""

We can fill the ``salt_water`` ``Container`` from the previous example to a total volume of 400 mL::

    salt_water = salt_water.fill_to(solvent=water, quantity='400 mL')

>>> print(salt_water.instructions)
Add 5.844 g of NaCl, 94.156 mL of H2O to a container.
Dilute with 100.0 mL of H2O.
Fill with 200.0 mL of H2O.

>>> print(salt_water.get_concentration(solute=salt, units='M'))
0.25

Transferring Between Containers
"""""""""""""""""""""""""""""""

You can transfer a volume of a solution to another container::

    new_container = Container(name='new container')
    salt_water = Container.create_solution('salt water', solute=salt, solvent=water,
                                           concentration='1 M', total_quantity='100 mL')

    salt_water, new_container = salt_water.transfer(source=salt_water, destination=new_container, quantity='10 mL')

    >>> print(salt_water.get_volume(unit='mL'))
    90.0

    >>> print(new_container.get_volume(unit='mL'))
    10.0

Diluting Stock Solutions
""""""""""""""""""""""""

In the previous examples, we made a solution by dissolving a solid into a liquid. You can also create a solution by diluting part of a stock solution::

    salt_water1M, salt_water500mM = Container.create_solution_from(name='salt water (0.5 M)', source=salt_water1M, solute=salt,
                                                                   solvent=water, concentration='0.5 M', quantity='10 mL')



- This requests the dilution of source ``salt_water1M`` with ``water``.
- The target concentration of ``salt`` in the new solution is ``0.5 M``.
- This requests the diluted solution have a volume of ``10 mL``.
- This sets the name of the new solution to ``'salt water (0.5 M)'``.
- Some, but necessarily all, of the source solution ``salt_water1M`` is used.
- The remainder of ``salt_water1M`` and the new diluted solution ``salt_water500mM`` are returned.
- If the desired concentration is not possible, a ``ValueError`` is raised.

>>> print(salt_water500mM.instructions)
Add 5.0 mL of H2O to 5.0 mL of salt water 1 M.

95 mL of the 1 M salt water solution remains.

>>> print(salt_water1M.get_volume(unit='mL'))
95.0

Using a solution as the solvent
-------------------------------

The solvent in ``create_solution_from`` can be a ``Container``, optionally containing some of the solute.
The remainder of the source solution, the remainder of the solvent solution, and the new solution are returned in that order.

Create the solvent solution::

    sodium_sulfate1M = Container.create_solution(name='sodium sulfate 1 M', solute=sodium_sulfate, solvent=triethylamine,
                                                 concentration='1 M', total_quantity='100 mL')

.. note:: Sodium sulfate is not really soluble in triethylamine. This is just an example.

Use ``sodium_sulfate1M`` and ``salt_water1M`` from above to create a 0.5 M salt solution::

    salt_water1M, sodium_sulfate1M, mixture = Container.create_solution_from(name='mixture', source=salt_water1M, solute=salt,
                                                                             solvent=sodium_sulfate1M, concentration='0.5 M', quantity='10 mL')

>>> print(mixture.instructions)
Add 5.0 mL of sodium sulfate 1 M to 5.0 mL of salt water 1 M.

>>> print(salt_water1M.get_volume(unit='mL'))
95.0

>>> print(sodium_sulfate1M.get_volume(unit='mL'))
95.0
