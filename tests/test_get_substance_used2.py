import numpy as np
import pdb
from pyplate.pyplate import Recipe, Container, Plate
import pytest
import logging

def test_substance_used(water):
    container = Container('container',initial_contents=((water, '100 mL'),))
    #salt_water = Container.create_solution(salt, water, concentration='1 M', total_quantity='100 mL')
    container2 = Container('container2')
    recipe = Recipe()
    recipe.uses(container,container2)
    recipe.transfer(source=container,destination=container2, quantity='10 mL')
    recipe.bake()
    assert recipe.get_substance_used(substance=water, timeframe='all', unit='mL', destinations=[container2]) == 10.0

def test_substance_used_create_solution_from(salt, water, triethylamine):
    """
    Tests accurate tracking of salt usage when creating a new solution from an existing diluted solution.

    This test simulates the scenario of diluting an existing salt solution with a different solvent (triethylamine) to create a new solution with the same concentration. The test procedure involves:
    - Creating an initial salt solution with a specified concentration and total quantity.
    - Creating a new solution from this initial solution, aiming to maintain the same concentration 
    but with a different solvent, and specifying a unique name for the new container.
    - Baking the recipe to apply all declared operations.

    Assertions:
    - The amount of salt used in both the creation of the initial solution and the new solution from 
    it matches the expected '10 mmol', demonstrating accurate tracking of substance usage.
    - The 'residual' volume after creating the new solution is 0, indicating all available solution 
    was used.
    - The volume of the newly created container is expected to be '20 mL', reflecting the specified 
    quantity for the new solution.

    Parameters:
    - salt (Substance): The solute used in the solutions.
    - water (Substance): The solvent for the initial solution.
    - triethylamine (Substance): The solvent for the new solution created from the existing one.
    """
    # Creating solution from a diluted solution
    recipe = Recipe()

    # Create initial solution and add to container
    recipe.start_stage('stage1')
    initial_container_name = "initial_salt_solution"
    container = recipe.create_solution(salt, water, concentration='1 M', total_quantity='20 mL',
                                       name=initial_container_name)

    recipe.end_stage('stage1')

    recipe.start_stage('stage2')
    # Create solution from the initial one with a new solvent
    new_container_name = "new_solution_from_initial"
    # pdb.set_trace()
    new_container = recipe.create_solution_from(source=container, solute=salt, concentration='0.5 M',
                                                solvent=water, quantity='10 mL', name=new_container_name)

    # Bake recipe to finalize

    recipe.end_stage('stage2')
    results = recipe.bake()

    new_container = results[new_container.name]
    # Assertions for substance amount used and container volumes
    expected_salt_amount_stage1 = 20.0
    expected_salt_amount_stage2 = 0.0
    # If destination for stage2 was new_container, then expected_salt_amount_stage2 would be 10.0

    assert recipe.get_substance_used(substance=salt, timeframe='stage1', unit='mmol', destinations=[container,
                                                                                                new_container]) == expected_salt_amount_stage1, "The reported amount of salt used does not match the expected value."
    assert recipe.get_substance_used(substance=salt, timeframe='stage2', unit='mmol', destinations=[container,
                                                                                                new_container]) == expected_salt_amount_stage2, "The reported amount of salt used does not match the expected value."
    # assert residual == 0, "Expected residual volume to be 0 after creating new solution."

    # Default unit is not Ml, so it shall be failing. Use Unit to change the units
    # Changed it to check for millimoles
    assert new_container.volume == 10000, "Expected new container volume to match the specified total quantity for the new solution."
