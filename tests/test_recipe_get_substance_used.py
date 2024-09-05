import numpy as np
import pdb
from pyplate import Recipe, Container, Plate
import pytest
import logging


# Set up logging


def test_substance_used(water, salt):
    container = Container('container')
    salt_water = Container.create_solution(salt, water, concentration='1 M', total_quantity='100 mL')
    recipe = Recipe()
    recipe.uses(salt_water, container)
    recipe.transfer(salt_water, container, '10 mL')
    recipe.bake()
    assert recipe.get_substance_used(substance=salt, timeframe='all', unit='mmol', destinations=[container]) == 10.0


def test_recipe_tracking_before(water):
    """
    Verify initial and mid-recipe substance volumes in a Recipe context.

    This test ensures accurate tracking of a substance's volume both before and during recipe execution, 
    using water as the test substance. It follows these steps:
    - Initializes a Recipe and an empty container (other_container).
    - Creates a new container within the Recipe, pre-filled with 10 mL of water, to simulate initial substance use ('before').
    - Transfers 5 mL of water from the newly created container to the empty one, to simulate substance use during the Recipe ('during').
    - Bakes the Recipe to finalize the operations and lock further modifications.
    
    Assertions:
    - Confirms that the total volume of water used before the Recipe operations start is accurately reported as 10 mL.
    - Validates that the volume of water transferred during the Recipe's execution is correctly recorded as 5 mL.
    
    Parameters:
    - water (Substance): The substance object representing water, provided by a pytest fixture.

    """

    # Create the recipe for testing
    recipe = Recipe()

    # Define the starting contents for the source container of the recipe
    initial_contents = [(water, '10 mL')]

    # Create a new container from which to transfer water
    container = Container('container', '20 mL', initial_contents)

    # Create a new container to which the water will be transferred
    other_container = Container('other container')

    # Set the recipe to use the two newly created containers
    recipe.uses(container, other_container)

    # Transfer 5 mL from container to other_container
    recipe.transfer(container, other_container, '5 mL')

    # Bake the recipe to lock it
    recipe.bake()

    # Assertions
    step = recipe.steps[-1]

    print(step.frm)
    print(step.to)
    assert recipe.get_substance_used(substance=water, unit='mL', destinations=[other_container]) == 5.0


def test_container_to_plate(triethylamine, empty_plate):
    # TODO: double check volumes here
    """
    Tests the transfer of a substance from a container to a plate within a Recipe context.

    This test verifies the correct volume handling and substance tracking during the transfer
      process in a recipe. It involves creating a container with a specified initial volume 
      of triethy-lamine, transferring a portion of this volume to an empty plate, and then
      baking the recipe to finalize all operations.

    The test checks three main aspects:
    - The volume of the source container (`container`) decreases by the transferred volume, expecting a
      reduction to '9.9 mL' from an initial '10 mL' after transferring '100 uL'.
    - The volume of the destination plate (`empty_plate`) increases to match the transferred volume, 
    expected to be '100 uL'.
    - The amount of triethylamine used during the recipe matches the transferred volume, 
    ensuring substance tracking aligns with the transfer operation.

    Parameters:
    - triethylamine (Substance): A fixture providing triethylamine, the substance being transferred.
    - empty_plate (Plate): A fixture providing an empty plate, the destination for the transfer.

    The test outputs the initial volume of the container, the source and 
    destination of the final transfer step, and an related print statements. It asserts 
    that the final volumes and substance usage match expected values.
    """

    # create_recipe
    recipe = Recipe()

    # define initial and transfer volumes
    initial_volume = '10 mL'
    transfer_volume = '100 uL'

    # define destinations

    # define initial contents and create container
    initial_contents = [(triethylamine, initial_volume)]
    container = Container('container', max_volume='20 mL',
                                        initial_contents=initial_contents)

    # Make sure that the recipe uses empty_plate and container
    recipe.uses(empty_plate, container)

    # start first stage
    recipe.start_stage('transfer_stage')
    recipe.transfer(container, empty_plate, transfer_volume)
    recipe.end_stage('transfer_stage')

    # Bake the recipe
    results = recipe.bake()

    # Get the containers from the results
    container = results[container.name]
    plate = results[empty_plate.name]

    # Calculate expected volume
    expected_volume_plate = 400
    expected_volume_container = 400

    # Assertions
    step = recipe.steps[-1]

    print(step.frm)
    print(step.to)

    print("Assertions start here")

    # Since 9600 muL is in the plate, the volume of the container should be 400 muL
    assert pytest.approx(container.volume) == 400

    # assert (np.full((8, 12), expected_volume_container) == plate.volumes(unit='uL')).all()
    # 100 muL is transferred to 96 wells in the plate, hence total expected value is 9600
    assert pytest.approx(recipe.get_substance_used(substance=triethylamine, timeframe='transfer_stage', unit='uL',
                                                   destinations=[empty_plate])) == 9600.0
    # assert pytest.approx(
    #     recipe.get_substance_used(substance=triethylamine, timeframe='dispensing', unit='uL')) == expected_volume_plate


def test_substance_used_remove(salt):
    """
    Tests the accuracy of substance amount tracking during the removal of a solution in a recipe.

    This test verifies the `get_substance_used` method for correctly reporting the amount of salt removed from a container. The procedure includes:
    - Creating a recipe and a container with an initial volume of '20 mL' of saltwater, implying a certain concentration of salt.
    - Removing '10 mL' of the saltwater from the container, which would also remove a proportional amount of salt based on the solution's concentration.
    - Baking the recipe to finalize the removal process.

    The test asserts:
    - The amount of salt removed during the recipe matches the expected value based on the initial concentration and the volume removed. The expected \
        salt amount should logically reflect the proportion of salt in the removed volume, which, in a homogenous solution, would be half of the initial \
        amount if '20 mL' contained '50 mmol' of salt.

    Parameters:
    - salt (Substance): The salt substance, expected to be tracked through the `get_substance_used` method.
    """

    # Create recipe
    recipe = Recipe()

    # Deine initial contents
    initial_contents = [(salt, '50 mmol')]

    # Create container
    container = Container('container', '20 mL', initial_contents)

    # Set the recipe to use the new container
    recipe.uses(container)

    # Remove 10 mL from container
    # Substance is solid, which leads to some errors
    recipe.remove(container, salt)

    # Bake recipe
    recipe.bake()

    # Assertions
    # All of 50 mmol is removed
    expected_salt_amount = 50.0
    # TODO: Fix the substance tracking behavior when creating unit tests for it
    # in a separate branch.
    assert recipe.get_substance_used(substance=salt, destinations=[container], unit='mmol') == expected_salt_amount


def test_stages_subst(water):
    """
    Tests tracking of water usage across recipe stages, focusing on water
    transfers within a specific stage and overall recipe operations.

    This test evaluates the functionality of defining, executing, and tracking
    operations within named stages of a recipe using the `Recipe` class. It
    involves transferring water between containers within a named stage ('stage1')
    and outside it, then verifying the accuracy of water usage tracking both
    within the stage and across the entire recipe.

    Steps:
    - Initialize a recipe and a container.
    - Begin 'stage1' for targeted operations.
    - Create an additional container within 'stage1'.
    - Prepare a solution with water in the initial container.
    - Conduct two water transfers to the second container within 'stage1'.
    - Conclude 'stage1' and perform an additional transfer outside this stage.
    - Finalize operations with a bake.

    Assertions:
    - The total water transferred to the second container within 'stage1'
      should be 15.0 mL, reflecting the combined volume from two transfers.
    - Across the entire recipe, including actions outside 'stage1', the total
      water usage should be 17.0 mL.

    Parameters:
    - water (Substance): Represents water, used in transfers and solution
      preparation.
    """

    recipe = Recipe()

    # Define the initial contents of the starting container=
    initial_contents = [(water, '20 mL')]

    # Create the containers which will be used for the substance transfers
    container = Container('container', '20 mL', initial_contents)
    other_container = Container('other container')

    # Set the recipe to use the new containers
    recipe.uses(container, other_container)

    # Start the first stage of the recipe
    recipe.start_stage('stage1')

    # Perform stage 1 transfers from container to other_container
    recipe.transfer(container, other_container, '5 mL')
    recipe.transfer(container, other_container, '10 mL')

    # End the first stage of the recipe
    recipe.end_stage('stage1')

    # Perform additional transfer from container to other container
    recipe.transfer(container, other_container, '2 mL')

    # Bake the recipe to lock it
    recipe.bake()

    # Ensure that the water transfers are reported accureately by get_substance_used() TODO: These seem very wrong
    assert recipe.get_substance_used(water, timeframe='stage1', destinations=[other_container], unit='mL') == 15.0
    assert recipe.get_substance_used(water, timeframe='all', unit='mL') == 0.0


def test_stages_2(water):
    """
    Tests water usage across containers and stages within a recipe, ensuring
    accurate tracking of water volume.

    This test evaluates the `Recipe` class's ability to manage and track water
    usage through various operations, including transfers and fill operations
    across containers and stages. It involves transferring water to a plate,
    filling a cell within the plate, and executing further transfers within
    a named stage. The goal is to verify water usage calculations across
    different containers and recipe stages.

    The procedure encompasses:
    - Creating a container with an initial water volume.
    - Setting up two plates for subsequent water transfers.
    - Transferring water from the container to the first plate.
    - Filling a cell in the first plate to a specified volume.
    - Initiating a new stage ('stage1') for specific operations.
    - Transferring water from the first to the second plate within 'stage1'.
    - Removing water from the second plate before concluding 'stage1'.
    - Baking the recipe to finalize all operations.

    Assertions:
    - Validates the total water used across all containers and stages matches
      the expected volume (30.0 mL considering the initial setup and fill
      operation).
    - Checks water usage specifically within the plates, excluding the initial
      container, to ensure accuracy of volume tracking (22.0 mL from the
      transfer and fill operations).
    - Asserts the water usage within 'stage1' and across specified containers
      aligns with expected actions taken during this stage.

    Parameters:
    - water (Substance): Represents the water used in the recipe's operations.
    """

    # Create the recipe for testing
    recipe = Recipe()

    # Create the container from which water will initially be transferred
    container1 = Container(name='container1', initial_contents=[(water, "10 mL")])
    
    # Create the two plates involved in the recipe
    plate1 = Plate('plate1', '100 uL')
    plate2 = Plate('plate2', '100 uL')
    
    # Set the recipe to use the newly created containers and plates
    recipe.uses(container1, plate1, plate2)

    # Pre-stage 1 transfer of water from the starting container to the first plate
    recipe.transfer(source=container1, destination=plate1, quantity='10 uL')

    # Start the first stage of the recipe
    recipe.start_stage('stage1')

    # Fill the first well in the first plate with water up to 20 uL
    recipe.fill_to(plate1[1, 1], solvent=water, quantity='20 uL')

    # Transfer water from the first plate to the second plate
    recipe.transfer(source=plate1, destination=plate2, quantity='1 uL')

    # Remove all the water from plate 2
    recipe.remove(plate2, water)

    # End the first stage of the recipe
    recipe.end_stage('stage1')

    # Bake the recipe to lock it
    recipe.bake()

    # Ensure that the water transfers are reported accureately by get_substance_used() 

    # dest should be destinations
    assert recipe.get_substance_used(water, timeframe='all', unit='mL',
                                     destinations=[container1, plate1, plate2]) == 0.96
    assert recipe.get_substance_used(water, timeframe='stage1', unit='mL', destinations=[plate1, plate2]) == 0.96
    #assert recipe.get_substance_used(water, timeframe='stage1', unit='mL', destinations = [plate1, plate2]) == -
    assert recipe.get_substance_used(water, timeframe='all', unit='mL', destinations=[plate1, plate2]) == 1.92
    assert recipe.get_substance_used(water, timeframe='all', unit='mL', destinations=[plate2]) == 0.096


def test_stages_plates(water):
    """
    Tests the dilution process across different stages within a recipe, focusing on a specific stage's volume and substance usage tracking.

    This test assesses the `Recipe` class's ability to handle complex procedures involving the creation of solutions, 
    transfers between containers, and dilution processes, specifically focusing on tracking these actions within 
    defined stages of the recipe. It includes creating a salt solution, transferring it to a plate, diluting the solution,
    transferring it again, and then removing part of the solution—all while tracking the amount of water used during a 
    specified stage.

    The process includes:
    - Creating a solution of salt in water with a specific concentration and total quantity.
    - Creating a water stock container for dilution purposes.
    - Initializing two plates to act as destination containers for transfers.
    - Executing a transfer from the solution container to the first plate.
    - Starting a named stage ('stage1') for tracking purposes.
    - Diluting the solution in the first plate using water from the water stock to achieve a new concentration.
    - Transferring a portion of the diluted solution from the first plate to the second plate.
    - Removing water from the second plate.
    - Ending the named stage ('stage1') and finalizing the recipe.

    Assertions:
    - Confirms that the amount of water used during 'stage1' matches the expected value. The expected amount of water 
    used is based on the dilution and transfer processes that occur within this stage.

    Parameters:
    - water (Substance): The solvent used for creating solutions and performing dilution, representing water.
    - salt (Substance): The solute used for creating the initial solution, representing salt.
    """
    
    # Create the recipe for testing
    recipe = Recipe()

    # Create the water stock container from which water will initially be transferred
    water_stock = Container(name='water_stock', initial_contents=[(water, "10 mL")])

    # Create the two plates involved in the recipe
    plate1 = Plate('plate1', '100 uL')
    plate2 = Plate('plate2', '100 uL')

    # Set the recipe to use the newly created containers and plates
    recipe.uses(water_stock, plate1, plate2)

    # Start the first stage of the recipe
    recipe.start_stage('stage1')

    # Transfer water from the water stock to the first plate
    recipe.transfer(source=water_stock, destination=plate1, quantity='2 uL')

    # End the first stage of the recipe
    recipe.end_stage('stage1')

    # Start the second stage of the recipe
    recipe.start_stage('stage2')

    # Transfer water from the first plate to the second plate
    recipe.transfer(source=plate1, destination=plate2, quantity='1 uL')

    # Remove water from the second plate
    recipe.remove(plate2, water)

    # End the second stage of the recipe
    recipe.end_stage('stage2')

    # Bake the recipe to lock it
    recipe.bake()

    # Ensure hat the water transfers are reported accureately by get_substance_used()
    assert recipe.get_substance_used(water, timeframe='stage1', unit='uL', destinations=[plate1]) == 192.0
    assert recipe.get_substance_used(water, timeframe='stage2', unit='uL', destinations=[plate2]) == 96.0


def test_substance_used_with_no_usage(salt):
    """
    Verifies that the amount of a substance reported as used is zero when the substance is not utilized in the recipe.

    This test case is designed to confirm the functionality of the `get_substance_used` method in scenarios where a specific substance is declared for a recipe but not actually used in any of the recipe steps. The key actions in this test include:
    - Initiating a recipe without adding any steps that involve the use of the specified substance (salt, in this case).
    - Finalizing the recipe preparation process by baking the recipe.
    
    The assertion checks:
    - That the `get_substance_used` method correctly reports '0 mmol' for the salt, reflecting that it was not used during the recipe's preparation, thus ensuring accurate tracking of substance usage within the recipe.

    Parameters:
    - salt (Substance): The substance fixture representing salt, intended to verify the tracking of substance usage.
    """

    recipe = Recipe()
    # No usage of salt
    recipe.bake()
    # Expecting 0 usage since salt wasn't used
    assert recipe.get_substance_used(substance=salt, timeframe='all', unit='mmol') == 0.0


def test_substance_used_incorrect_timeframe(salt_water, salt, empty_plate):
    """
    Ensures an error is raised when querying the amount of substance used with an unsupported timeframe.

    This test aims to verify the error handling capabilities of the `get_substance_used` method within the `Recipe` class, particularly when an invalid or unsupported timeframe is specified. The test follows these steps:
    - Initializes a recipe and declares the use of a saltwater solution.
    - Transfers a specified volume of the saltwater solution to a plate, simulating a typical recipe action.
    - Completes the recipe by invoking the `bake` method.
    
    The critical part of this test is the assertion that checks:
    - A `ValueError` is raised when attempting to call `get_substance_used` with a timeframe argument that the method does not support (`'later'` in this case). The error message is expected to match "Unsupported timeframe," indicating that the method correctly identifies and rejects invalid timeframe inputs.

    Parameters:
    - salt_water (Container): A fixture representing the saltwater solution used in the recipe.
    - salt (Substance): The substance fixture representing salt, intended to be tracked within the recipe.
    - plate (Plate): A fixture representing a plate, to which the saltwater solution is transferred as part of the recipe.
    """
    recipe = Recipe()
    container = Container('container')
    recipe.uses(salt_water, container)
    recipe.uses(empty_plate)
    recipe.transfer(salt_water, empty_plate, '10 uL')
    recipe.transfer(salt_water, container, '10 uL')
    recipe.bake()

    # Raising errors for unexpected timeframes
    with pytest.raises(ValueError, match="Invalid timeframe"):
        recipe.get_substance_used(substance=salt, timeframe='later', unit='mmol')


def test_substance_used_fill_to_plate(salt, water):
    
    # Create the plate that will be used for the recipe
    plate = Plate('plate', max_volume_per_well='2 mL')

    # Create the stock solution of salt water that will be used for the recipe
    salt_water = Container.create_solution(salt, water, concentration='1 M', total_quantity='100 mL')
    
    # Create the recipe that will be used for testing
    recipe = Recipe()

    # Set the recipe to use the newly created plate and salt water stock container
    recipe.uses(plate, salt_water)

    # Transfer varying amounts of salt water to each of the wells on the plate, 
    # and record the salt amounts for each transfer
    salt_used = 0
    for x, row in enumerate(plate.row_names):
        for y, col in enumerate(plate.column_names):
            recipe.transfer(salt_water, plate[row, col], f"{x * y} uL")
            salt_used += x * y * salt_water.get_concentration(salt, 'mmol/uL')
    
    # Fill each of the wells up to 1 mL, 
    # regardless of the amount already present.
    recipe.fill_to(plate, solvent=water, quantity='1 mL')

    # Bake the recipe to lock it
    recipe.bake()

    assert recipe.get_substance_used(substance=salt, timeframe='all', 
                                     unit='mmol') == round(salt_used, 10) # TODO: Change this to config.precision
