.. _recipe_01:

========================
Creating PyPlate Objects
========================

These recipes demonstrates how to create PyPlate objects. PyPlate objects are the
building blocks of Recipes.

``from pyplate import Substance, Container, Plate`` imports the main classes.


"""""""""""""""""""
Creating Substances
"""""""""""""""""""

::

    # Create a solid
    salt = Substance.Solid(name='NaCl', mol_weight=58.44)

    # Create a liquid
    water = Substance.Liquid(name='H2O', mol_weight=18.01528, density=1.0)

    # Create an enzyme
    amylase = Substance.Enzyme(name='Amylase')


"""""""""""""""""""
Creating Containers
"""""""""""""""""""

::

    # Create an empty container
    vial = Container(name='vial')

    # Maximum volume can be specified
    vial = Container(name='vial', max_volume='10 mL')

    # Initial contents can be specified
    salt_water = Container(name='salt_water', contents=[(salt, '5 mg'), (water, '10 mL')])


"""""""""""""""
Creating Plates
"""""""""""""""

::

        # Create a 96-well plate
        plate = Plate(name='96-well plate', max_volume_per_well='120 uL')

        # Create a 384-well plate
        plate = Plate(name='384-well plate', max_volume_per_well='120 uL', rows=16, cols=24)

        # Create a 96-well plate with a make label
        plate = Plate(name='96-well plate', max_volume_per_well='120 uL', make='thermofisher')