.. _users_guide_02:

Working with Containers
=======================

The following examples use these ``Substance``\ s:

::

    salt = Substance.solid(name='NaCl', mol_weight=58.44)
    water = Substance.liquid(name='H2O', mol_weight=18.01528, density=1.0)
    sodium_sulfate = Substance.solid(name='sodium_sulfate', mol_weight=142.04)
    triethylamine = Substance.liquid(name='triethylamine', mol_weight=101.19, density=0.726)


Concentrations
""""""""""""""

Concentration can be define in molarity, molality, or in ratio of units:

Examples:

.. hlist::
    :columns: 3

    - '0.1 M'
    - '0.1 m'
    - '0.1 g/mL'
    - '0.01 umol/10 uL'
    - '5 %v/v'
    - '5 %w/v'
    - '5 %w/w'

.. note:: For '%w/v', the units are defined as ``default_weight_volume_units`` in the configuration file.
    (The default is 'g/mL')

Creating solutions
""""""""""""""""""

Create a 1M solution of salt water::

    salt_water = Container.create_solution(solute=salt, solvent=water, concentration='1 mol/L', total_quantity='100 mL')


.. Rework create_solution so concentration='1 g/mL' works.

>>> print(salt_water.instructions)
Add 5.844 g of NaCl, 94.156 mL of H2O to a container.

All ``Container``\ s are immutable. Any operations on a ``Container`` will return a new, modified ``Container`` object.

Diluting solutions
""""""""""""""""""

Dilute the solution to 0.5M (Results in 200 mL of 0.5M solution)::

    salt_water = salt_water.dilute(solute=salt, solvent=water, concentration='0.5 M')

>>> print(salt_water.instructions)
Add 5.844 g of NaCl, 94.156 mL of H2O to a container.
Dilute with 100.0 mL of H2O.

Filling Containers
""""""""""""""""""

Filling a solution to a certain volume::

    salt_water = salt_water.fill_to(solvent=water, quantity='400 mL')

>>> print(salt_water.instructions)
Add 5.844 g of NaCl, 94.156 mL of H2O to a container.
Dilute with 100.0 mL of H2O.
Fill with 200.0 mL of H2O.
0.25

You can get the current concentration with respect to the solute:

>>> print(salt_water.get_concentration(solute=salt, units='M'))
0.25


Serial dilution
"""""""""""""""

You can use one source solution to create multiple dilutions.

- Enough of the source solution and solvent is used to create the new solutions.
- The source solution is returned with the unused quantity.
- The solvent can be a ``Container``, optionally containing some of the solute.

  - If this is the case, the remaining solvent is returned with the new solution.
- The order of the return is: source solution, [solvent,] new solution.
- If the desired concentration is not possible, a ``ValueError`` is raised.

::

    salt_water1M = Container.create_solution(name='salt water 1 M', solute=salt, solvent=water,
                                             concentration='1 M', total_quantity='100 mL')

Create a 0.5 M solution from the 1M solution with a volume of 10 mL::

    salt_water1M, salt_water500mM = Container.create_solution_from(name='salt_water0.5M', source=salt_water1M, solute=salt,
                                                                   solvent=water, concentration='0.5 M', quantity='10 mL')

>>> print(salt_water500mM.instructions)
Add 5.0 mL of H2O to 5.0 mL of salt water 1 M.

You can get the current volume of a ``Container``

>>> print(salt_water500mM.get_volume(unit='mL'))
10.0

Create a 0.2 M solution from the 1M solution with a volume of 10 mL::

    salt_water1M, salt_water200mM = Container.create_solution_from(name='salt_water0.2M', source=salt_water1M, solute=salt,
                                                                   solvent=water, concentration='0.2 M', quantity='10 mL')

>>> print(salt_water200mM.instructions)
Add 8.0 mL of H2O to 2.0 mL of salt water 1 M.

The 1 M salt water solution now has 93 mL left.

>>> print(salt_water1M.get_volume(unit='mL'))
93.0

Using a solution as the solvent
-------------------------------

You can use a solution as the solvent for a new solution.

Create the solvent solution::

    sodium_sulfate1M = Container.create_solution(name='sodium sulfate 1 M', solute=sodium_sulfate, solvent=triethylamine,
                                                 concentration='1 M', total_quantity='100 mL')

.. note::
    Sodium sulfate is not really soluble in triethylamine. This is just an example.

Use sodium_sulfate1M and salt_water1M to create a 0.5 M salt solution::

    salt_water1M, sodium_sulfate1M, mixture = Container.create_solution_from(name='mixture', source=salt_water1M, solute=salt,
                                                                             solvent=sodium_sulfate1M, concentration='0.5 M', quantity='10 mL')

>>> print(mixture.instructions)
Add 5.0 mL of sodium sulfate 1 M to 5.0 mL of salt water 1 M.
