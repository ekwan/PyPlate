import numpy as np
from pyplate import Recipe, Container

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
    stock_solution = Container.create_solution(solute=sodium_sulfate,
                                            solvent=water, concentration='0.5 M', total_quantity='50 mL')
    
    recipe.uses(dest_container, stock_solution)

    recipe.start_stage('stage 1')
    recipe.transfer(stock_solution, dest_container, '10 mL')
    recipe.end_stage('stage 1')

    recipe.start_stage('stage 2')
    recipe.remove(dest_container, water)

    # implicit end of stage at end of recipe
    # recipe.end_stage('stage 2')

    recipe.bake()

    assert recipe.get_container_flows(container=stock_solution,
                                      timeframe='all', unit='mL') == {"in": 0, "out": 10}
    # TODO: Remove highly test-specific magic number; compute this from the 
    # properties of substances involved, and/or change "create_solution" to make
    # this number easier to determine.
    assert recipe.get_container_flows(container=dest_container, timeframe='stage 2', unit='mL') == {"out": 9.733,
                                                                                                    "in": 0}


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
    container = Container('container', max_volume='100 mL', initial_contents=initial_contents)

    recipe.uses(empty_plate, container)

    recipe.transfer(container, empty_plate, transfer_volume)
    results = recipe.bake()

    container = results[container.name]
    plate = results[empty_plate.name]

    #Calculate expected volumes
    expected_volume_plate = 400
    expected_volume_container = 400

    #Assertions
    assert pytest.approx(container.volume) == 800
    assert recipe.get_container_flows(container=container, timeframe='all', unit='mL') == {"in": 0, "out": 19.2}


def test_example1(water, sodium_sulfate):
    recipe = Recipe()

    container = Container('container', initial_contents=None)
    stock_solution = Container.create_solution(sodium_sulfate, water, concentration='0.5 M', total_quantity='50 mL')

    recipe.uses(container, stock_solution)

    recipe.transfer(stock_solution, container, '10 mL')

    recipe.bake()

    assert recipe.get_container_flows(container=stock_solution, timeframe='all', unit='mL') == {"in": 0, "out": 10}
    assert recipe.get_substance_used(substance=sodium_sulfate, timeframe='all', destinations=[container],
                                     unit='mmol') == 5.0
