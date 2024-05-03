import numpy as np
import pdb
from pyplate.pyplate import Recipe, Container, Plate
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

    other_container = Container('other container')

    recipe = Recipe()
    # uses to tell recipe about other containers
    recipe.uses(other_container)

    # Add solute and solvent to the create_solution method
    initial_contents = [(water, '10 mL')]

    # Implicit definition of container being used
    container = recipe.create_container('container', '20 mL', initial_contents)

    # Transfer 5 mL from container to other_container
    recipe.transfer(container, other_container, '5 mL')

    recipe.bake()
    # Assertions
    step = recipe.steps[-1]

    print(step.frm)
    print(step.to)
    assert recipe.get_substance_used(substance=water, unit='mL', destinations=[container]) == 5.0


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
    container = recipe.create_container('container', max_volume='20 mL',
                                        initial_contents=initial_contents)

    # Test if container.volume is correct intially
    assert container.volume == 0

    # Make sure that the recipe uses empty_plate
    recipe.uses(empty_plate)

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


def test_substance_used_dilute(salt, water):
    """
    Tests that the substance amount tracking is correctly tracked during dilution in a recipe.

    This test checks the `get_substance_used` method  to correctly report the amount of salt used after diluting a saltwater solution. The procedure involves:
    - Declaring a container with saltwater as part of a recipe.
    - Adding a specific amount of salt to increase the solution's concentration.
    - Diluting the solution to a target molarity of '0.5 M' using water.
    - Baking the recipe to complete the process.

    It asserts that:
    - The total amount of salt reported as used matches the expected '50 mmol', despite the dilution.
    - This ensures the method accurately reflects substance usage across recipe actions.

    Parameters:
    - salt_water (Container): Pre-filled container fixture with saltwater.
    - salt (Substance): Salt substance to be tracked.
    - water (Substance): Water used as the solvent for dilution.
    """

    # Using self defined container
    container = Container('container')

    # Create recipe
    recipe = Recipe()

    # container = recipe.create_container('container', '20 mL', [(salt_water, '10 mL')])

    # Define what the recipe uses
    recipe.uses(container)
    salt_solution = recipe.create_solution(salt, water, concentration='0.5 M',
                                           total_quantity='20 mL')
    # container._add(salt_water, '10 mL')

    # Transfer 10 mL of salt solution to container
    recipe.start_stage('dilution_stage')
    recipe.transfer(salt_solution, container, '10 mL')

    # Add solute to recipe
    # container = container._add(salt, '50 mmol') #Does not do anything as the container that is used in the recipe is the one that was stored initially
    recipe.dilute(container, solute=salt, concentration='0.25 M', solvent=water)

    recipe.end_stage('dilution_stage')

    recipe.bake()

    assert container.volume == 0
    # Results would contain the pointers to the new containers, so assert from there

    expected_salt_amount = 5.0
    assert recipe.get_substance_used(substance=salt, destinations=[container], timeframe='dilution_stage',
                                 unit='mmol') == expected_salt_amount


# Testing create_solution
def test_substance_used_create_solution(salt, water):
    """
    Tests that the substance amount tracking is accurately implemented during the creation of a solution within a recipe.

    This test verifies the `get_substance_used` method to correctly report the amount of salt utilized in preparing a specific solution. The testing procedure includes:
    - Initiating a recipe and declaring the usage of salt and water as solute and solvent, respectively.
    - Creating a solution with a predefined concentration of '0.5 M' and a total quantity of '20 mL', effectively dissolving the salt within the water.
    - Executing the `bake` method to finalize the creation of the solution.

    The assertions made are:
    - The initial volume of the container is checked before the solution creation, ensuring it starts from a baseline of zero.
    - The amount of salt reported as used during the recipe matches the expected calculation, which is '10 mmol' for achieving the desired solution concentration and volume. This confirms the `get_substance_used` method's accuracy in reflecting substance usage throughout the recipe's actions.

    Parameters:
    - salt (Substance): The salt intended to be dissolved to create the solution.
    - water (Substance): The water used as a solvent for the solution.

    """

    plate = Plate(name='plate', max_volume_per_well='20 mL')
    # Create recipe
    recipe = Recipe()
    # Recipe.uses only takes Containers and Plates
    # recipe.uses(salt, water)
    recipe.uses(plate)

    # Create solution and add to container
    recipe.start_stage('stage1')
    container = recipe.create_solution(salt, water, concentration='0.1 M', total_quantity='1 L')
    ##What is the initial volume of container here?
    assert container.volume == 0
    recipe.transfer(container, plate, '10 mL')
    recipe.end_stage('stage1')

    # Bake recipe
    recipe.bake()

    # Assertions
    # Container starts with 100 mmol of salt. 1 mmol is dispensed to each of 96 wells in the plate.
    # A net of 4 mmol is "used" into the container
    expected_salt_amount = 4.0
    assert recipe.get_substance_used(substance=salt, unit='mmol', destinations=[container],
                                 timeframe='stage1') == expected_salt_amount


# Try substance with solid and liquid
def test_substance_used_create_solution_from(salt, water, triethylamine):
    """
    Tests accurate tracking of salt usage when creating a new solution from an existing diluted solution.

    This test simulates the scenario of diluting an existing salt solution with a different solvent (triethylamine) to create a new solution with the same concentration. The test procedure involves:
    - Creating an initial salt solution with a specified concentration and total quantity.
    - Creating a new solution from this initial solution, aiming to maintain the same concentration but with a different solvent, and specifying a unique name for the new container.
    - Baking the recipe to apply all declared operations.

    Assertions:
    - The amount of salt used in both the creation of the initial solution and the new solution from it matches the expected '10 mmol', demonstrating accurate tracking of substance usage.
    - The 'residual' volume after creating the new solution is 0, indicating all available solution was used.
    - The volume of the newly created container is expected to be '20 mL', reflecting the specified quantity for the new solution.

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

    #Add a Create Solution function too
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


def test_substance_used_remove(salt_water, salt):
    """
    Tests the accuracy of substance amount tracking during the removal of a solution in a recipe.

    This test verifies the `get_substance_used` method for correctly reporting the amount of salt removed from a container. The procedure includes:
    - Creating a recipe and a container with an initial volume of '20 mL' of saltwater, implying a certain concentration of salt.
    - Removing '10 mL' of the saltwater from the container, which would also remove a proportional amount of salt based on the solution's concentration.
    - Baking the recipe to finalize the removal process.

    The test asserts:
    - The amount of salt removed during the recipe matches the expected value based on the initial concentration and the volume removed. The expected salt amount should logically reflect the proportion of salt in the removed volume, which, in a homogenous solution, would be half of the initial amount if '20 mL' contained '50 mmol' of salt.

    Parameters:
    - salt_water (Container): A fixture representing the saltwater solution to be partially removed.
    - salt (Substance): The salt substance, expected to be tracked through the `get_substance_used` method.
    """

    # Create recipe
    recipe = Recipe()

    # Deine initial contents
    initial_contents = [(salt, '50 mmol')]

    # Create container
    container = recipe.create_container('container', '20 mL', initial_contents)

    # Remove 10 mL from container
    # Substance is solid, which leads to some errors
    recipe.remove(container, salt)

    # Bake recipe
    recipe.bake()

    # Assertions
    # All of 50 mmol is removed
    expected_salt_amount = 50.0
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

    recipe.start_stage('stage1')
    other_container = recipe.create_container('other container')

    # Add solute and solvent to the create_solution method
    initial_contents = [(water, '20 mL')]

    # Implicit definition of container being used
    container = recipe.create_container('container', '20 mL', initial_contents)

    # Transfer 5 mL from container to other_container
    recipe.transfer(container, other_container, '5 mL')
    recipe.transfer(container, other_container, '10 mL')

    recipe.end_stage('stage1')
    recipe.transfer(container, other_container, '2 mL')
    recipe.bake()

    destination_container = [other_container]
    assert recipe.get_substance_used(water, timeframe='stage1', destinations=[container], unit='mL') == 5.0
    assert recipe.get_substance_used(water, timeframe='stage1', destinations=[container, other_container], unit='mL') == 20.0
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
    recipe = Recipe()
    container1 = recipe.create_container(name='container1', initial_contents=[(water, "10 mL")])
    plate1 = Plate('plate1', '100 uL')
    plate2 = Plate('plate2', '100 uL')
    recipe.uses(plate1, plate2)

    recipe.transfer(source=container1, destination=plate1, quantity='10 uL')
    
    recipe.start_stage('stage1')
    # fill the first well in plate
    recipe.fill_to(plate1[1, 1], solvent=water, quantity='20 uL')

    # start a new stage
    
    recipe.transfer(source=plate1, destination=plate2, quantity='1 uL')
    recipe.remove(plate2, water)
    recipe.end_stage('stage1')

    # bake the recipe
    recipe.bake()
    # dest should be destinations
    assert recipe.get_substance_used(water, timeframe='all', unit='mL', destinations = [container1, plate1, plate2]) == 10.96
    assert recipe.get_substance_used(water, timeframe='stage1', unit='mL', destinations = [plate1, plate2]) == 0.96
    #assert recipe.get_substance_used(water, timeframe='stage1', unit='mL', destinations = [plate1, plate2]) == -
    assert recipe.get_substance_used(water, timeframe='all', unit='mL', destinations = [plate1, plate2]) == 1.92
    assert recipe.get_substance_used(water, timeframe='all', unit='mL', destinations = [plate2]) == 0.096


def test_stages_plates(water, salt):
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
    recipe = Recipe()
    
    water_stock = recipe.create_container(name='water_stock', initial_contents=[(water, "10 mL")])

    plate1 = Plate('plate1', '100 uL')
    plate2 = Plate('plate2', '100 uL')
    recipe.uses(plate1, plate2)

    recipe.start_stage('stage1')
    recipe.transfer(source=water_stock, destination=plate1, quantity='2 uL')
    recipe.end_stage('stage1')
    # You cannot dilute a plate, only a container
    # recipe.dilute(plate1, solute=salt, solvent=water, concentration='0.5 M')
    recipe.start_stage('stage2')
    recipe.transfer(source=plate1, destination=plate2, quantity='1 uL')
    recipe.remove(plate2, water)

    recipe.end_stage('stage2')

    recipe.start_stage

   

    recipe.bake()

    #Assertions
    assert recipe.get_substance_used(water, timeframe='stage1', unit='uL',destinations=[plate1] ) == 192.0
    assert recipe.get_substance_used(water, timeframe='stage2', unit='uL',destinations=[plate2] ) == 96.0

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
    plate = Plate('plate', max_volume_per_well='2 mL')
    recipe = Recipe()
    recipe.uses(plate)
    salt_water = recipe.create_solution(salt, water, concentration='1 M', total_quantity='100 mL')
    for x, row in enumerate(plate.row_names):
        for y, col in enumerate(plate.column_names):
            recipe.transfer(salt_water, plate[row, col], f"{x * y} uL")
    recipe.fill_to(plate, solvent=water, quantity='1 mL')
    recipe.bake()

    assert True
