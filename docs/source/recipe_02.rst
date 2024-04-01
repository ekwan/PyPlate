.. _recipe_02:

=======================
Working with Containers
=======================

The following examples use these Substances:

::

    salt = Substance.Solid(name='NaCl', mol_weight=58.44)
    water = Substance.Liquid(name='H2O', mol_weight=18.01528, density=1.0)
    sodium_sulfate = Substance.Solid(name='sodium_sulfate', mol_weight=142.04)
    triethylamine = Substance.Liquid(name='triethylamine', mol_weight=101.19, density=0.726)

""""""""""""""""""
Creating solutions
""""""""""""""""""

::

    # Create a 1M solution of salt water
    salt_water = Container.create_solution(solute=salt, solvent=water, concentration='1 M', total_quantity='100 mL')

    print(salt_water.instructions)
    # "Add 5.844 g of NaCl, 94.156 mL of H2O to a container."

    # Dilute the solution to 0.5M (Results in 200 mL of 0.5M solution)
    salt_water = salt_water.dilute(solute=salt, solvent=water, concentration='0.5 M')

    # Filling a solution to a certain volume
    salt_water = salt_water.fill_to(solvent=water, quantity='400 mL')

    print(salt_water.get_concentration(salt, 'M'))
    # 0.25


"""""""""""""""
Serial dilution
"""""""""""""""

::

    salt_water1M = Container.create_solution(name='salt_water1M', solute=salt, solvent=water,
                                             concentration='1 M', total_quantity='100 mL')

    # Create 10 mL of 0.5 M and 0.2 M solutions from the 1M solution
    salt_water1M, salt_water500mM = Container.create_solution_from(name='salt_water0.5M', source=salt_water1M, solute=salt,
                                                                   solvent=water, concentration='0.5 M', quantity='10 mL')

    print(salt_water500mM.instructions)
    # "Add 5.0 mL of H2O to 5.0 mL of salt_water1M."

    salt_water1M, salt_water200mM = Container.create_solution_from(name='salt_water0.2M', source=salt_water1M, solute=salt,
                                                                   solvent=water, concentration='0.2 M', quantity='10 mL')

    print(salt_water200mM.instructions)
    # "Add 8.0 mL of H2O to 2.0 mL of salt_water1M."

    # salt_water1M now has 93 mL of 1M solution left


""""""""""""""""""""""""""
More complicated solutions
""""""""""""""""""""""""""

::

    sodium_sulfate1M = Container.create_solution(name='sodium_sulfate1M', solute=sodium_sulfate, solvent=triethylamine,
                                                 concentration='1 M', total_quantity='100 mL')

    # Use sodium_sulfate1M and salt_water1M to create a 0.5 M salt water solution
    salt_water1M, sodium_sulfate1M, mixture = Container.create_solution_from(name='mixture', source=salt_water1M, solute=salt,
                                                                             solvent=sodium_sulfate1M, concentration='0.5 M', quantity='10 mL')
    print(mixture.instructions)
    # "Add 5.0 mL of sodium_sulfate1M to 5.0 mL of salt_water1M."


    # Another way of creating the same mixture
    mixture = Container(name='mixture')
    salt_water1M, mixture = Container.transfer(source=salt_water1M, destination=mixture, quantity='5 mL')
    sodium_sulfate1M, mixture = Container.transfer(source=sodium_sulfate1M, destination=mixture, quantity='5 mL')

    print(mixture.instructions)
    # """
    # Create a container.
    # Transfer 5.0 mL of salt_water1M to mixture
    # Transfer 5.0 mL of sodium_sulfate1M to mixture
    # """

