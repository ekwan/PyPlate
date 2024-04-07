.. _users_guide_01:

Creating PyPlate Objects
========================

These recipes demonstrates how to create PyPlate objects. PyPlate objects are the
building blocks of Recipes.

``from pyplate import Substance, Container, Plate`` imports the main classes.

Specifying Units
""""""""""""""""

* Units are specified as strings with a number and a unit abbreviation. (‘1 mmol’, ‘10.2 g’, ‘10 uL’, …)
* The basic units of pyplate are moles, grams, liters, and activity units. (‘mol’, ‘g’, ‘L’, ‘U’)
* Any time units are required, metric prefixes may be specified. (‘mg’, ‘umol’, ‘dL’, …)


Creating Substances
"""""""""""""""""""

* A ``Substance`` is a solid, liquid, or enzyme.
* Enzymes are like solids, but are specified in *units of activity* ('U') instead of mass.
* Enzymes and solids contribute volume to the Containers they are in.
* Solids' density is defined in pyplate.yaml as ``default_solid_density``. (1 g/mL in default config)
* Enzymes' density is defined in pyplate.yaml as ``default_enzyme_density``. (1 U/mL in default config)

Create a solid::

    salt = Substance.Solid(name='NaCl', mol_weight=58.44)

Create a liquid::

    water = Substance.Liquid(name='H2O', mol_weight=18.01528, density=1.0)

Create an enzyme::

    amylase = Substance.Enzyme(name='Amylase')


Creating Containers
"""""""""""""""""""

* A ``Container`` holds defined amounts of a set of ``Substance``\ s and can have a maximum volume.
* If any operation would cause the volume of the ``Container`` to exceed the maximum volume, a ``ValueError`` is raised.

Create an empty Container::

    vial = Container(name='vial')

Create an empty Container, specifying the maximum volume::

    vial = Container(name='vial', max_volume='10 mL')

Create a Container with 5 mg of salt and 10 mL of water::

    salt_water = Container(name='salt_water', max_volume='100 mL',
                           contents=[(salt, '5 mg'), (water, '10 mL')])


Creating Plates
"""""""""""""""

* ``Plate``\ s are rectangular arrays of ``Container``\ s.
* Plates must have a defined maximum volume per well.
* If any operation would cause the volume of a well to exceed the maximum volume, a ``ValueError`` is raised.
* The default plate type is a 96-well plate.
* Plates can be created with any number of rows and columns.
* Different row and column labels can be specified. (Each label must be unique.)
* Plates can be created with a make label to specify the manufacturer.

Create a 96-well plate::

        plate = Plate(name='96-well plate', max_volume_per_well='120 uL')

Create a 384-well plate::

        plate = Plate(name='384-well plate', max_volume_per_well='120 uL', rows=16, cols=24)

Create a 96-well plate with a make label::

        plate = Plate(name='96-well plate', max_volume_per_well='120 uL', make='thermofisher')

Create a 96-well plate with custom row and column labels::

        plate = Plate(name="custom plate", max_volume_per_well="50 uL", rows=['i', 'ii', 'iii'], columns=['a', 'b', c'])


Locations on a Plate and slices
"""""""""""""""""""""""""""""""

PyPlate follows the ``pandas`` convention of having both integer- and
label-based indices for referencing wells in ``Plate``\ s. When row or
column specifiers are provided as integers, they are assumed to be
integer indices (1, 2, 3, …). When specifiers are provided as strings,
they are assumed to be label indices (“A”, “B”, “C”, …).

By default, rows in plates are given alphabetical labels “A”, “B”, “C”,
… and columns in plates are given numerical labels “1”, “2”, “3”.
However, rows and columns are always given integer indices 1, 2, 3, ….
For example, ``“B:3”``, ``('B', 3)``, and ``(2,3)`` both refer to well B3.

Here are some ways to refer to a specific well:

-  **String Method**: ``“A:1”``
-  **Tuple Method**: ``(‘A’, 1)``

You can refer to multiple wells as a list::

    plate[[('A', 1), ('B', 2), ('C', 3), 'D:4']]

Slicing syntax is supported:

-  In addition, you can provide python slices of wells with 1-based
   indexes::

    plate[:3], plate[:, :3], plate['C':], plate[1, '3':]

