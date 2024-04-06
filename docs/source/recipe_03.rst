.. _recipe_03:

====================
Working with Recipes
====================

The following examples use these objects:

::

    from pyplate import Substance, Container, Plate, Recipe

    salt = Substance.solid(name='NaCl', mol_weight=58.44)
    water = Substance.liquid(name='H2O', mol_weight=18.01528, density=1.0)
    sodium_sulfate = Substance.solid(name='sodium_sulfate', mol_weight=142.04)
    triethylamine = Substance.liquid(name='triethylamine', mol_weight=101.19, density=0.726)
    dimethylformamide = Substance.liquid(name='dimethylformamide', mol_weight=73.095, density=0.944)
    methanol = Substance.liquid(name='methanol', mol_weight=32.04, density=0.791)
    solvents = [water, triethylamine, dimethylformamide, methanol]
    dtbbpy = Substance.solid(name='dtbbpy', mol_weight=268.404)
    dbrbpy = Substance.solid(name='dbrbpy', mol_weight=313.98)
    ttbtpy = Substance.solid(name='ttbtpy', mol_weight=401.598)
    iminophosph = Substance.solid(name='iminophosph', mol_weight=380.391)
    n_ligands = [dtbbpy, dbrbpy, ttbtpy, iminophosph]
    dppp = Substance.solid(name='dppp', mol_weight=412.453)
    dppb = Substance.solid(name='dppb', mol_weight=426.48)
    p_ligands = [dppp, dppb]
    LiCl = Substance.solid(name='Lithium Chloride', mol_weight=42.394)
    pfl = Substance.solid(name='Potassium Fluoride', mol_weight=58.096)
    PBr = Substance.solid(name='Potassium Bromide', mol_weight=119.002)
    salts = [LiCl, pfl, PBr]
    Ni_catalyst = Substance.solid(name='Nickel(II) bromide ethylene glycol dimethyl ether complex', mol_weight=308.623)
    Pd_catalyst = Substance.solid(name='Bis(acetonitrile)dichloropalladium(II)', mol_weight=259.432)
    Zn = Substance.solid(name='Zinc', mol_weight=65.39)


"""""""
Creating a simple Recipe
"""""""

::

    plate = Plate('plate', max_volume_per_well='60 uL')

    recipe = Recipe()
    recipe.uses(plate)

    water_stock = recipe.create_container(name='water_stock', initial_contents=[(water, '100 mL')])
    # Dispense 10 uL of water into each well of the plate.
    recipe.transfer(source=water_stock, destination=plate, quantity='10 uL')

    # Bake the recipe. The results is a dictionary of object names to the
    # resulting objects after the recipe has been baked.
    results = recipe.bake()

    # 960 uL of water has been dispensed from the water_stock container.
    print(results['water_stock'])
    # "Container (water_stock) (99.04 mL of (['H2O (LIQUID): 5.498 mol'])"

    # Each step of the recipe has instructions that can be printed.
    for step in recipe.steps:
        print(step.instructions)

    # "Create container water_stock with initial contents: [(H2O (LIQUID), '100 mL')]."
    # "Transfer 10 uL from water_stock to plate[:]."

"""""""
Creating a full permutation in a recipe
"""""""

- Each row of the plate will contain a different Ni and P ligand combination.
- Each column of the plate will contain a different solvent and salt combination.

::

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
