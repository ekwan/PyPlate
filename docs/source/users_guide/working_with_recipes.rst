.. _working_with_recipes:

Working with Recipes
====================
If you have a complicated series of operations to perform, you can combine them into a ``Recipe``.

- ``Recipes``\ s allow you to "compile" steps to ensure that the proposed experimental steps are physically reasonable.
- ``Container``\ s and ``Plate``\ s must be declared in the recipe before they can be used. (``Substance``\ s cannot be declared.)
- The recipe must be "baked" to execute the steps and retrieve the resulting objects.
- The final state of the ``Plate`` and ``Container`` objects in the recipe are returned from ``bake()`` as a dictionary of object names to objects.
- After baking, the recipe will contain a list of steps (``recipe.steps``).
- Each step has instructions that can be printed and visualizations that can be displayed.

The following examples use these :ref:`objects <used_objects>`.

Creating a simple Recipe
""""""""""""""""""""""""

Let's create a 96-well ``Plate`` and register it with the ``Recipe``::

    plate = Plate('plate', max_volume_per_well='60 uL')

    recipe = Recipe()
    recipe.uses(plate)


In addition to creating containers using the ``Container`` class, we can also do so within a ``Recipe``::

    water_stock = recipe.create_container(name='water stock', initial_contents=[(water, '100 mL')])

The new container is returned so that it may be used in later recipe steps. The container is automatically declared to the recipe.

Let's transfer 10 uL of water into each of the wells of ``plate``::


    # Dispense 10 uL of water into each well of the plate.
    recipe.transfer(source=water_stock, destination=plate, quantity='10 uL')


In order to actually perform the operations above, we need to "bake" the recipe::

    results = recipe.bake()

    # results == {'plate': <Plate>, 'water stock': <Container>}

The results contain the final state of ``Container``\ s and ``Plate``\ s in the recipe.
These objects are immutable, so the original objects are not modified.

Let's retrieve the final state of our objects::

    water_stock = results['water stock']
    plate = results['plate']


Let's look at the contents after the recipe:

>>> print(water_stock.get_volume(unit='mL'))
99.04

960 uL of water has been dispensed into each well of the plate from the water_stock container.
99.04 mL of water remains in the water_stock container.

Let's look at the instructions for each step of the recipe:

>>> for step in recipe.steps:
>>>     print(step.instructions)
Create container water_stock with initial contents: [(H2O (LIQUID), '100 mL')].
Transfer 10 uL from water_stock to plate[:].


Using Stages
""""""""""""

Stages are useful for organizing the steps of a recipe into logical sections. |Br|
The amount of material used in each stage can be queried, see below.


Let's see a simple example where this is helpful::

    plate = Plate(name='plate', max_volume_per_well='60 uL')
    recipe = Recipe()
    recipe.uses(plate)

    recipe.start_stage('stock solution')
    water_stock = recipe.create_container(name='water stock', initial_contents=[(water, '100 mL')])
    recipe.end_stage('stock solution')

    recipe.start_stage('dispensing')
    recipe.transfer(source=water_stock, destination=plate, quantity='10 uL')

- Stages cannot overlap.
- The last stage is automatically closed when the recipe is baked.

Let's bake the recipe::

    results = recipe.bake()

We can query the amount of water "used" during the dispensing stage of the ``Recipe``:

>>> print(recipe.get_substance_used(substance=water, timeframe='dispensing', unit='mL'))
0.96

For more details, see :ref:`usage_tracking`.

Transfer Between Plates
"""""""""""""""""""""""

Let's create two plates and transfer the contents of one to the other::

    plate1 = Plate('plate1', max_volume_per_well='60 uL')
    plate2 = Plate('plate2', max_volume_per_well='60 uL')

    recipe = Recipe()
    recipe.uses(plate1)
    recipe.uses(plate2)

    water_stock = recipe.create_container(name='water stock', initial_contents=[(water, '100 mL')])
    recipe.transfer(source=water_stock, destination=plate1, quantity='10 uL')
    recipe.transfer(source=plate1, destination=plate2, quantity='3 uL')

Transfers between plates must involve regions of the same shape. (Use slices if necessary :ref:`locations`) |br|
This transfer works because both plates are 8x12.

::

    results = recipe.bake()
    plate1 = results['plate1']
    plate2 = results['plate2']


`plate1` will now contain 7 uL of water in each of its wells, and `plate2` will contain 3 uL of water in each of its wells.

>>> plate1.dataframe(unit='uL')

.. figure:: /images/plate1.png

>>> plate2.dataframe(unit='uL')

.. figure:: /images/plate2.png

Extracting data from RecipeSteps
""""""""""""""""""""""""""""""""

After baking, a recipe has a list of steps. You can extract data from these steps using `RecipeStep.dataframe()`

During the second step, 10 uL of water is transferred from the water_stock container to plate1.

Let's demonstrate how to extract the data from this step:

>>> recipe.steps[1].dataframe(data_source='destination', mode='final', unit='uL')

.. figure:: /images/plate_dataframe_10uL.png
   :scale: 50%

In the third step, 3 uL of water is transferred from plate1 to plate2.

You can get the volume of each well in the source plate after the step:

>>> recipe.steps[2].dataframe(data_source='source', mode='final', unit='uL')

.. figure:: /images/plate_dataframe_7uL.png
   :scale: 50%

You can also get the volume of each well of the destination plate after the step:

>>> recipe.steps[2].dataframe(data_source='destination', mode='final', unit='uL')

.. figure:: /images/plate_dataframe_3uL.png
   :scale: 50%

We can query the amount of specific substances added in each step:

>>> recipe.steps[2].dataframe(data_source='destination', mode='delta', substance=water, unit='umol')

.. figure:: /images/plate_dataframe_water_umol.png
   :scale: 50%

.. _cross_coupling_liquid_handling:

Using Source Plates
"""""""""""""""""""

Suppose you have a cross-electrophile coupling reaction of the form  X + Y --> Z. |br|
You have 8 variations of coupling partner X1, X2, ..., X8 and 12 variations of coupling partner Y1, Y2, ..., Y12. |br|
Together, the full product of these would make 96 potential products Z. |br|
Now suppose you want to test a number of different conditions, sampling 1 condition per 96 well plate. |br|
You can make a source plate where Xs are in rows and Ys are in columns::

    # x_solutions is the list of solutions for each X partner
    # y_solutions is the list of solutions for each Y partner
    plate = Plate('source_plate', max_volume_per_well='240 uL')
    recipe = Recipe()
    recipe.uses(plate, *x_solutions, *y_solutions)
    for row, x in enumerate(x_solutions):
        for column, y in enumerate(y_solutions):
            # Row and column indices in PyPlate are 1-indexed
            recipe.transfer(source=x, destination=plate[row + 1, column + 1], quantity='60 uL')
            recipe.transfer(source=y, destination=plate[row + 1, column + 1], quantity='60 uL')


Now, transfer this source plate to various destination plates::

    destination_plates = [Plate(f'destination_plate_{i}', max_volume_per_well='60 uL') for i in range(1, 5)]
    recipe.uses(*destination_plates)
    for i, destination_plate in enumerate(destination_plates):
        recipe.transfer(source=plate, destination=destination_plate, quantity='10 uL')

If you have two P-ligands and two N-ligands, you can distribute them across the four destination plates::

    # n_solutions is the list of solutions for each N ligand
    # p_solutions is the list of solutions for each P ligand
    for n_i, n in enumerate(n_solutions):
        for p_i, p in enumerate(p_solutions):
            plate_index = n_i * 2 + p_i   # 0, 1, 2, 3
            recipe.transfer(source=n, destination=destination_plates[plate_index], quantity='10 uL')
            recipe.transfer(source=p, destination=destination_plates[plate_index], quantity='10 uL')

Creating a full permutation in a recipe
"""""""""""""""""""""""""""""""""""""""

- Each row of the plate will contain a different Ni and P ligand combination.
- Each column of the plate will contain a different solvent and salt combination.

::

    solvents = [water, triethylamine, dimethylformamide, methanol]
    n_ligands = [dtbbpy, dbrbpy, ttbtpy, iminophosph]
    p_ligands = [dppp, dppb]
    salts = [LiCl, pfl, PBr]

    plate = Plate('plate', max_volume_per_well='60 uL')

    recipe = Recipe()
    recipe.uses(plate)

    for x, solvent in enumerate(solvents):
        for y, ligand in enumerate(n_ligands):
            # Four ligands and four solvents. Each solution is dispensed over two rows and three columns
            ligand_solution = recipe.create_solution(name=f'{ligand.name} in {solvent.name}', solute=ligand,
                                                     solvent=solvent, concentration='10 umol/10 uL', total_quantity='1 mL')
            print(2*y, 2*y+1, 3*x, 3*x+2)
            recipe.transfer(source=ligand_solution, destination=plate[2*y+1:2*y+2, 3*x+1:3*x+3], quantity='10 uL')
        for y, ligand in enumerate(p_ligands):
            # Two ligands and four solvents. Each solution is dispensed over four rows and three columns
            ligand_solution = recipe.create_solution(name=f'{ligand.name} in {solvent.name}', solute=ligand,
                                                     solvent=solvent, concentration='10 umol/10 uL', total_quantity='1 mL')
            recipe.transfer(source=ligand_solution, destination=plate[y+1::2, 3*x+1:3*x+3], quantity='10 uL')

    for x1, solvent in enumerate(solvents):
        for x2, salt in enumerate(salts):
            # Three salts and four solvents. Each solution is dispensed into one column.
            salt_solution = recipe.create_solution(name=f'{salt.name} in {solvent.name}', solute=salt,
                                                   solvent=solvent, concentration='10 umol/10 uL', total_quantity='1 mL')
            print(x1*3 + x2 + 1)
            recipe.transfer(source=salt_solution, destination=plate[:, x1*3 + x2 + 1], quantity='10 uL')

    results = recipe.bake()
    plate = results['plate']

    # print first well in each row
    for row in plate.row_names:
        print(plate[row, 1].get())

    # [[Container (well A,1) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Lithium Chloride (SOLID): 10.0 umol', 'H2O (LIQUID): 1.264 mmol'])]]
    # [[Container (well B,1) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppb (SOLID): 10.0 umol', 'Lithium Chloride (SOLID): 10.0 umol', 'H2O (LIQUID): 1.256 mmol'])]]
    # [[Container (well C,1) (0.03/0.06 mL of (['dbrbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Lithium Chloride (SOLID): 10.0 umol', 'H2O (LIQUID): 1.238 mmol'])]]
    # [[Container (well D,1) (0.03/0.06 mL of (['dbrbpy (SOLID): 10.0 umol', 'dppb (SOLID): 10.0 umol', 'Lithium Chloride (SOLID): 10.0 umol', 'H2O (LIQUID): 1.231 mmol'])]]
    # [[Container (well E,1) (0.03/0.06 mL of (['ttbtpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Lithium Chloride (SOLID): 10.0 umol', 'H2O (LIQUID): 1.19 mmol'])]]
    # [[Container (well F,1) (0.03/0.06 mL of (['ttbtpy (SOLID): 10.0 umol', 'dppb (SOLID): 10.0 umol', 'Lithium Chloride (SOLID): 10.0 umol', 'H2O (LIQUID): 1.182 mmol'])]]
    # [[Container (well G,1) (0.03/0.06 mL of (['iminophosph (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Lithium Chloride (SOLID): 10.0 umol', 'H2O (LIQUID): 1.202 mmol'])]]
    # [[Container (well H,1) (0.03/0.06 mL of (['iminophosph (SOLID): 10.0 umol', 'dppb (SOLID): 10.0 umol', 'Lithium Chloride (SOLID): 10.0 umol', 'H2O (LIQUID): 1.194 mmol'])]]


    # print first row in each column
    for column in plate.column_names:
        print(plate[1, column].get())

    # [[Container (well A,1) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Lithium Chloride (SOLID): 10.0 umol', 'H2O (LIQUID): 1.264 mmol'])]]
    # [[Container (well A,2) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Potassium Fluoride (SOLID): 10.0 umol', 'H2O (LIQUID): 1.255 mmol'])]]
    # [[Container (well A,3) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Potassium Bromide (SOLID): 10.0 umol', 'H2O (LIQUID): 1.221 mmol'])]]
    # [[Container (well A,4) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Lithium Chloride (SOLID): 10.0 umol', 'triethylamine (LIQUID): 163.3 umol'])]]
    # [[Container (well A,5) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Potassium Fluoride (SOLID): 10.0 umol', 'triethylamine (LIQUID): 162.2 umol'])]]
    # [[Container (well A,6) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Potassium Bromide (SOLID): 10.0 umol', 'triethylamine (LIQUID): 157.9 umol'])]]
    # [[Container (well A,7) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Lithium Chloride (SOLID): 10.0 umol', 'dimethylformamide (LIQUID): 294.0 umol'])]]
    # [[Container (well A,8) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Potassium Fluoride (SOLID): 10.0 umol', 'dimethylformamide (LIQUID): 292.0 umol'])]]
    # [[Container (well A,9) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Potassium Bromide (SOLID): 10.0 umol', 'dimethylformamide (LIQUID): 284.1 umol'])]]
    # [[Container (well A,10) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Lithium Chloride (SOLID): 10.0 umol', 'methanol (LIQUID): 562.1 umol'])]]
    # [[Container (well A,11) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Potassium Fluoride (SOLID): 10.0 umol', 'methanol (LIQUID): 558.2 umol'])]]
    # [[Container (well A,12) (0.03/0.06 mL of (['dtbbpy (SOLID): 10.0 umol', 'dppp (SOLID): 10.0 umol', 'Potassium Bromide (SOLID): 10.0 umol', 'methanol (LIQUID): 543.2 umol'])]]

    # Print the volume of each well in the plate
    print(plate.volumes(unit='uL'))

    # [[30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30.]
    #  [30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30.]
    #  [30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30.]
    #  [30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30.]
    #  [30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30.]
    #  [30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30.]
    #  [30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30.]
    #  [30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30. 30.]]

.. _used_objects:

Objects used in examples
""""""""""""""""""""""""

::

    from pyplate import Substance, Container, Plate, Recipe

    salt = Substance.solid(name='NaCl', mol_weight=58.44)
    water = Substance.liquid(name='H2O', mol_weight=18.01528, density=1.0)
    sodium_sulfate = Substance.solid(name='sodium_sulfate', mol_weight=142.04)
    triethylamine = Substance.liquid(name='triethylamine', mol_weight=101.19, density=0.726)
    dimethylformamide = Substance.liquid(name='dimethylformamide', mol_weight=73.095, density=0.944)
    methanol = Substance.liquid(name='methanol', mol_weight=32.04, density=0.791)
    dtbbpy = Substance.solid(name='dtbbpy', mol_weight=268.404)
    dbrbpy = Substance.solid(name='dbrbpy', mol_weight=313.98)
    ttbtpy = Substance.solid(name='ttbtpy', mol_weight=401.598)
    iminophosph = Substance.solid(name='iminophosph', mol_weight=380.391)
    dppp = Substance.solid(name='dppp', mol_weight=412.453)
    dppb = Substance.solid(name='dppb', mol_weight=426.48)
    LiCl = Substance.solid(name='Lithium Chloride', mol_weight=42.394)
    pfl = Substance.solid(name='Potassium Fluoride', mol_weight=58.096)
    PBr = Substance.solid(name='Potassium Bromide', mol_weight=119.002)
    Ni_catalyst = Substance.solid(name='Nickel(II) bromide ethylene glycol dimethyl ether complex', mol_weight=308.623)
    Pd_catalyst = Substance.solid(name='Bis(acetonitrile)dichloropalladium(II)', mol_weight=259.432)
    Zn = Substance.solid(name='Zinc', mol_weight=65.39)
