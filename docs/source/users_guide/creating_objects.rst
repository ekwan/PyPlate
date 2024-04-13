.. _creating_objects:

Creating PyPlate Objects
========================

These examples demonstrates how to create PyPlate objects. PyPlate objects are the
building blocks of Recipes.

``from pyplate import Substance, Container, Plate`` imports the main classes.

Creating Substances
"""""""""""""""""""

- A ``Substance`` is a solid, liquid, or enzyme.
- Solids
  - All solids have the same default density as defined in pyplate.yaml as ``default_solid_density``. (1 g/mL in default config)
  - Different solids have different molecular weights.
- Liquids
  - Different liquids have different molecular weights and densities.
- Enzymes
  - Enzymes are like solids, but are specified in *units of activity* ('U') instead of mass.
  - The density of enzymes is defined in pyplate.yaml as ``default_enzyme_density``. (1 U/mL in default config)
- All substances contribute volume to the Containers they are in.

Create a solid::

    salt = Substance.Solid(name='NaCl', mol_weight=58.44)

Create a liquid::

    water = Substance.Liquid(name='H2O', mol_weight=18.01528, density=1.0)

Create an enzyme::

    amylase = Substance.Enzyme(name='Amylase', specific_activity='100 U/mg')


Creating Containers
"""""""""""""""""""

A ``Container`` holds defined amounts of a set of ``Substance``\ s and can have a maximum volume.

Create an empty Container::

    vial = Container(name='vial')

Create an empty Container, specifying the maximum volume::

    vial = Container(name='vial', max_volume='10 mL')

Create a Container with 5 mg of salt and 10 mL of water::

    salt_water = Container(name='salt_water', max_volume='100 mL',
                           contents=[(salt, '5 mg'), (water, '10 mL')])


If any operation would cause the volume of the ``Container`` to exceed the maximum volume, a ``ValueError`` is raised.

>>> Container(name='vial', max_volume='10 mL', contents=[(water, '20 mL')])
ValueError: Exceeded maximum volume

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

