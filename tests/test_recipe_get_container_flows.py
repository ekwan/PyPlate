import numpy as np
from pyplate.pyplate import Recipe, Container, Substance

import pytest

# def test_simple_volume_used(salt_water, water):
#     container = Container('container', initial_contents=[(water, '20 mL')])
#     recipe = Recipe()
#     recipe.uses(salt_water, container)
#     recipe.transfer(salt_water, container, '10 mL')
#     #recipe.transfer
#     recipe.bake()
    
#     #Assertions
#     assert recipe.volume_used(container, 'all', 'mL') == 100

def test_container_flows(sodium_sulfate, water):
    
    recipe = Recipe()
    dest_container = Container('dest_container', initial_contents=None)
    recipe.uses(dest_container)

    stock_solution = recipe.create_solution(solute=sodium_sulfate, 
                                            solvent=water, concentration='0.5 M', total_quantity='50 mL')
    recipe.start_stage('stage 1')
    recipe.transfer(stock_solution, dest_container, '10 mL')
    recipe.end_stage('stage 1')

    recipe.start_stage('stage 2')
    recipe.remove(dest_container, water)

    # implicit end of stage at end of recipe
    # recipe.end_stage('stage 2')

    recipe.bake()

    assert recipe.get_container_flows(container=stock_solution, 
                                      timeframe='all', unit='g') == {"in": 50, "out": 10}
    assert recipe.get_container_flows(container=dest_container, timeframe='stage 2', unit='mL') == {"out": 9.29, "in": 0}


def test_fill_to(salt, water):
    """
    Tests the accuracy of volume tracking for a container filled to a specified volume within a recipe.

    This test case checks if the `Recipe` class's volume tracking mechanism accurately records the volume of water added to an initially empty container using the `fill_to` method. After the container is filled and the recipe is baked, the volume used by the container is assessed.

    The procedure includes:
    - Initializing an empty container.
    - Using the `fill_to` method to add a specified volume of water to the container as part of a recipe.
    - Finalizing the recipe by baking it, which confirms all actions including the fill operation.
    
    Assertions:
    - The `volume_used` method should return a dictionary indicating the total volume of 'in' as 10.0 mL, representing the water added to the container, and 'out' as 0.0 mL, indicating no volume was removed from the container throughout the recipe's execution.

    Parameters:
    - salt (Substance): Has not been directly used in this test
    - water (Substance): The substance used to fill the container, representing water in this scenario.
    """

    water_container = Container('container')
    recipe = Recipe().uses(water_container)
    recipe.fill_to(water_container, water, '10 mL')
    recipe.bake()

    assert recipe.get_container_flows(container=water_container, timeframe='all', unit='mL') == {"in": 10.0, "out": 0.0}

def test_volume_used_container_to_plate(dmso, empty_plate):
    """
    Tests the transfer of a specified volume from a container to a plate and checks the volume tracking functionality.

    This test ensures that the `Recipe` class can accurately track the volume transferred from a container containing a specific volume of DMSO to an empty plate within the recipe's execution. It involves creating a container with a given initial volume of DMSO, transferring a portion of this volume to an empty plate, and then finalizing the recipe to assess the volume tracking accuracy.

    The procedure includes:
    - Initializing a container with an initial volume of DMSO.
    - Transferring a specified volume of DMSO from this container to an empty plate as part of the recipe.
    - Baking the recipe to confirm all actions and transfers.

    Assertions:
    - Initially asserts that the container's volume is correctly set to 0 after creation, assuming creation does not immediately affect the volume.
    - Verifies the volume of DMSO transferred to the plate matches the expected volume, ensuring correct volume tracking during the transfer.
    - Checks that the `volume_used` method returns accurate 'in' and 'out' volumes for the container, reflecting the DMSO volume transferred out of it.

    Parameters:
    - dmso (Substance): The substance used for the initial volume in the container, representing dimethyl sulfoxide in this scenario.
    - empty_plate (Plate): A fixture representing an empty plate, the destination for the DMSO transfer.
    """
    recipe = Recipe()

    initial_volume = '20 mL'
    transfer_volume = '200 uL'

    initial_contents = [(dmso, initial_volume)]
    container = recipe.create_container('container', max_volume = '100 mL', initial_contents= initial_contents)

    assert container.volume == 0

    recipe.uses(empty_plate)

    recipe.transfer(container, empty_plate, transfer_volume)
    results = recipe.bake()

    container = results[container.name]
    plate = results[empty_plate.name]

    #Calculate expected volumes
    expected_volume_plate = 400
    expected_volume_container = 400

    #Assertions
    assert pytest.approx(container.volume) == 800
    assert recipe.get_container_flows(container=container, timeframe='all', unit = 'mL') == {"in": 20, "out": 19.2}

def test_get_container_flows_create_solution(sodium_sulfate, water, empty_plate):
    """
    Tests the creation of a solution within a recipe and its volume and substance usage tracking.

    This test verifies the `Recipe` class's feature to accurately track both the volume and the amount of a 
    substance used when creating a solution. The scenario involves creating a sodium sulfate solution in water 
    with a specified concentration and total quantity. After creating the solution and finalizing the recipe, the test assesses the accuracy of substance usage and volume tracking.

    The process includes:
    - Initializing a recipe and declaring the usage of sodium sulfate and water.
    - Creating a solution of sodium sulfate in water with a concentration of 0.5 M and a total quantity of 50 mL.
    - Asserting that the initial volume of the container (before baking the recipe) is set to 0, 
    assuming that the container's volume is not immediately affected upon creation.
    - Baking the recipe to finalize the creation of the solution.

    Assertions:
    - Verifies that the amount of sodium sulfate used matches the expected amount necessary to achieve the specified 
    concentration and total quantity of the solution, which is calculated as '25.0 mmol'.
    - Confirms that the `volume_used` method accurately reflects the total volume of the solution created ('in' as 50 mL) 
    and no volume removed ('out' as 0 mL) from the container over the course of the recipe.

    Parameters:
    - sodium_sulfate (Substance): The substance used to create the solution, representing sodium sulfate.
    - water (Substance): The solvent used in the solution, representing water.
    """


    recipe = Recipe()

    container = recipe.create_solution(solute=sodium_sulfate, solvent=water, concentration='0.5 M', total_quantity='50 mL')

    recipe.uses(empty_plate)
    recipe.start_stage('stage 1')

    #Both these transfers result in the same output
    recipe.transfer(container, empty_plate, '10 uL')
    #recipe.transfer(container, empty_plate, '10 mg')
    recipe.end_stage('stage 1')

    container2 = Container('container2', initial_contents=[(water, '20 mL')], max_volume = '100 mL')
    recipe.start_stage('stage 2')
    recipe.uses(container2)
    recipe.transfer(container, container2, '5 mL')
    
    recipe.end_stage('stage 2')

    recipe.bake()

    #Assertions
    

    #Calculations : 50 mL * 0.5 M = 25 mmol
    #Transferred = 10*10^-3 * 0.5 = 5*10^-3 mmol
    #Num wells = 96
    #Total = 5*10^-3 * 96 = 0.48 mmol
    #Remaining = 25 - 0.48 = 24.52 mmol
    expected_amount = 24.52
    assert recipe.get_substance_used(substance=sodium_sulfate, timeframe='stage 1', unit='mmol', destinations=[empty_plate]) == 0.48
    assert recipe.get_container_flows(container=container, timeframe='stage 1', unit= 'mL') == {"in": 0, "out": 0.96}

    #Do we want container to only be a container? Should we expand it to plates as well? 
    #assert recipe.get_container_flows(container=empty_plate, timeframe='all', unit= 'mL') == {"in": 0.96, "out": 0}

    #When using mg, it converts it with the density
    assert recipe.get_container_flows(container=container, timeframe='all', unit= 'mL') == {"in": 50, "out": 5.96}
    assert recipe.get_container_flows(container=container2, timeframe='stage 2', unit= 'mL') == {"in": 5, "out": 0}
    assert recipe.get_substance_used(substance=sodium_sulfate, timeframe='all', unit='mmol', destinations=[container]) == 22.02


def test_enzyme(lipase):

    recipe = Recipe()
    container = recipe.create_container('container', initial_contents=[(lipase, '10 U')])

    container2 = recipe.create_container('container2', initial_contents=None)

    recipe.transfer(container, container2, '5 U')

    recipe.bake()
    assert recipe.get_container_flows(container=container, timeframe='all', unit='U') == {"in": 10, "out": 5}
    assert recipe.get_container_flows(container=container2, timeframe='all', unit='U') == {"in": 5, "out": 0}

def test_enzyme_fill_to(lipase):

    recipe = Recipe()
    container = recipe.create_container('container', initial_contents=None)

    recipe.fill_to(container, lipase, '10 mg')

    container2 = recipe.create_container('container2', initial_contents=None)

    recipe.transfer(container, container2, '5 mg')

    recipe.bake()

    #Specific activity is 10 U/mg. So 10 mg = 100 U

    assert recipe.get_container_flows(container=container, timeframe='all', unit='U') == {"in": 100, "out": 50}
    assert recipe.get_container_flows(container=container2, timeframe='all', unit='U') == {"in": 50, "out": 0}


def test_dilute(sodium_sulfate, water):
    """
    Tests the dilution process within a recipe and evaluates volume tracking for the involved container.

    This test checks the functionality of diluting a solution within a recipe and accurately tracking the volume adjustments in the container used for dilution. Initially, a solution of sodium sulfate in water is created with a specific concentration and quantity. A portion of this solution is then transferred to a container, which is subsequently diluted to a lower concentration. The test assesses the accuracy of the volume tracking before and after dilution.

    The procedure includes:
    - Creating an empty container and initializing a recipe.
    - Creating a sodium sulfate solution with a 1 M concentration and a total quantity of 10 mL.
    - Transferring 5 mL of this solution into the container.
    - Diluting the solution within the container to a new concentration of 0.25 M 
    using water as the solvent.
    - Baking the recipe to finalize the dilution process.

    Assertions:
    - Ensures that the container's volume is correctly tracked through the dilution process.
      Initially, the container is expected to have a volume of 0 mL
    - Verifies that the `volume_used` method accurately reports the total volume of liquid added ('in') as 20 mL and the volume removed ('out') as 0 mL, based on the dilution calculation.

    Parameters:
    - sodium_sulfate (Substance): The substance used for creating the initial solution, representing sodium sulfate.
    - water (Substance): The solvent used in both the solution creation and the dilution process, representing water.
    """

    container = Container('container')

    recipe = Recipe()

    recipe.uses(container)

    sodium_sulfate_solution = recipe.create_solution(sodium_sulfate, water,concentration= '1 M', total_quantity = '10 mL' )
    
    recipe.transfer(sodium_sulfate_solution,container, '5 mL')

    recipe.dilute(container, solute=sodium_sulfate, concentration = '0.25 M', solvent = water)
    recipe.bake()

    #steps = recipe.steps[-1]

    assert container.volume == 0

    assert pytest.approx(recipe.get_container_flows(container = container, timeframe='all', unit = 'mL')) == {"in": 20.0, "out":0.0}
    #assert recipe.volume_used(container = container, timeframe='all', unit = 'mL') == {"in": 20, "out":0.0}


def test_example1(water, sodium_sulfate): 

    recipe = Recipe()
    container = recipe.create_container('container', initial_contents=None)

    stock_solution = recipe.create_solution(sodium_sulfate, water, concentration='0.5 M', total_quantity='50 mL')

    recipe.transfer(stock_solution, container, '10 mL')

    recipe.bake()

    assert recipe.get_container_flows(container=stock_solution, timeframe='all', unit='mL') == {"in": 50, "out": 10}
    assert recipe.get_substance_used(substance=sodium_sulfate, timeframe='all', destinations=[container], unit='mmol') == 5.0