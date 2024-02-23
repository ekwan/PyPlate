import numpy as np

from pyplate.pyplate import Recipe, Container
import pytest


def test_volume_used_fill_to(salt, water):
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

    assert recipe.volume_used(container=water_container, timeframe='all', unit='mL') == {"in": 10.0, "out": 0.0}


def test_simple_volume_used(salt_water, water):
    """
    Tests the volume tracking function of a container within a recipe.

    This test ensures that the `Recipe` class accurately tracks the volume of a substance transferred into and out of a container throughout the recipe's execution. 
    The test simulates a scenario where a specified volume of saltwater from one container is transferred into a container already containing water, and then the recipe is baked.

    The process involves:
    - Creating a container with an initial volume of water.
    - Declaring the use of both the saltwater and the container within the recipe.
    - Transferring a specified volume of saltwater into the container.
    - Baking the recipe

    Assertions:
    - The `volume_used` method should accurately reflect the total volume transferred into the container ('in') and the total volume transferred out (if applicable) during the entire recipe process. 
    - The expected outcome is a dictionary with keys 'in' and 'out', where 'in' is 10.0 mL (the volume transferred into the container) and 'out' is 10 mL
    Parameters:
    - salt_water (Container): A fixture representing the saltwater solution used in the transfer.
    - water (Substance): The substance fixture representing water, initially present in the container.
    """
    container = Container('container', initial_contents=[(water, '20 mL')])
    recipe = Recipe()
    recipe.uses(salt_water, container)
    recipe.transfer(salt_water, container, '10 mL')
    #recipe.transfer
    recipe.bake()
    
    #Assertions
    assert recipe.volume_used(container=container, timeframe='all', unit = 'mL') == {"in": 10.0, "out": 10}

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
    assert pytest.approx(container.volume) == expected_volume_plate
    assert pytest.approx(recipe.volume_used(container=container, timeframe='all', unit = 'uL') == {"in": 0, "out": 400})


def test_volume_used_create_solution(sodium_sulfate, water):
    """
    Tests the creation of a solution within a recipe and its volume and substance usage tracking.

    This test verifies the `Recipe` class's feature to accurately track both the volume and the amount of a substance used when creating a solution. The scenario involves creating a sodium sulfate solution in water with a specified concentration and total quantity. After creating the solution and finalizing the recipe, the test assesses the accuracy of substance usage and volume tracking.

    The process includes:
    - Initializing a recipe and declaring the usage of sodium sulfate and water.
    - Creating a solution of sodium sulfate in water with a concentration of 0.5 M and a total quantity of 50 mL.
    - Asserting that the initial volume of the container (before baking the recipe) is set to 0, assuming that the container's volume is not immediately affected upon creation.
    - Baking the recipe to finalize the creation of the solution.

    Assertions:
    - Verifies that the amount of sodium sulfate used matches the expected amount necessary to achieve the specified concentration and total quantity of the solution, which is calculated as '25.0 mmol'.
    - Confirms that the `volume_used` method accurately reflects the total volume of the solution created ('in' as 50 mL) and no volume removed ('out' as 0 mL) from the container over the course of the recipe.

    Parameters:
    - sodium_sulfate (Substance): The substance used to create the solution, representing sodium sulfate.
    - water (Substance): The solvent used in the solution, representing water.
    """


    recipe = Recipe()
    recipe.uses(sodium_sulfate, water)

    container = recipe.create_solution(sodium_sulfate, water, concentration='0.5 M', total_quantity='50 mL')
    assert container.volume == 0

    recipe.bake()

    #Assertions
    expected_amount = '25.0 mmol'
    assert recipe.amount_used(substance=sodium_sulfate, timeframe='all', unit='mmol') == expected_amount
    assert recipe.volume_used(container=container, timeframe='all', unit= 'mL') == {"in": 50, "out": 0}


def test_volume_used_dilute(sodium_sulfate, water):
    """
    Tests the dilution process within a recipe and evaluates volume tracking for the involved container.

    This test checks the functionality of diluting a solution within a recipe and accurately tracking the volume adjustments in the container used for dilution. Initially, a solution of sodium sulfate in water is created with a specific concentration and quantity. A portion of this solution is then transferred to a container, which is subsequently diluted to a lower concentration. The test assesses the accuracy of the volume tracking before and after dilution.

    The procedure includes:
    - Creating an empty container and initializing a recipe.
    - Creating a sodium sulfate solution with a 1 M concentration and a total quantity of 10 mL.
    - Transferring 5 mL of this solution into the container.
    - Diluting the solution within the container to a new concentration of 0.25 M using water as the solvent.
    - Baking the recipe to finalize the dilution process.

    Assertions:
    - Ensures that the container's volume is correctly tracked through the dilution process. Initially, the container is expected to have a volume of 0 mL, which may need clarification as it contradicts the transfer and dilution steps.
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

    assert pytest.approx(recipe.volume_used(container = container, timeframe='all', unit = 'mL')) == {"in": 20.0, "out":0.0}
    #assert recipe.volume_used(container = container, timeframe='all', unit = 'mL') == {"in": 20, "out":0.0}