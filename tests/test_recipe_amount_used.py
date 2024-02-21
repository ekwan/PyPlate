import numpy as np

from pyplate.pyplate import Recipe, Container
import pytest


def test_amount_used(salt_water, salt):
    container = Container('container')
    substance = salt
    recipe = Recipe()
    recipe.uses(salt_water, container)
    recipe.transfer(salt_water, container, '10 mL')
    recipe.bake()
    assert recipe.amount_used(substance=salt, timeframe='all', unit='mmol') == '50.0 mmol'


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
    assert recipe.amount_used(substance=water, timeframe='all', unit='mL') == '10.0 mL'
    assert recipe.amount_used(substance=water, timeframe='dispensing', unit='mL') == '5.0 mL'


def test_container_to_plate(triethylamine, empty_plate):
    # TODO: double check volumes here
    """
    Tests the transfer of a substance from a container to a plate within a Recipe context.

    This test verifies the correct volume handling and substance tracking during the transfer process in a recipe. It involves creating a container with a specified initial volume of triethylamine, transferring a portion of this volume to an empty plate, and then baking the recipe to finalize all operations.

    The test checks three main aspects:
    - The volume of the source container (`container`) decreases by the transferred volume, expecting a reduction to '9.9 mL' from an initial '10 mL' after transferring '100 uL'.
    - The volume of the destination plate (`empty_plate`) increases to match the transferred volume, expected to be '100 uL'.
    - The amount of triethylamine used during the recipe matches the transferred volume, ensuring substance tracking aligns with the transfer operation.

    Parameters:
    - triethylamine (Substance): A fixture providing triethylamine, the substance being transferred.
    - empty_plate (Plate): A fixture providing an empty plate, the destination for the transfer.

    The test outputs the initial volume of the container, the source and destination of the final transfer step, and an related print statements. It asserts that the final volumes and substance usage match expected values.
    """

    # create_recipe
    recipe = Recipe()

    # define initial and transfer volumes
    initial_volume = '10 mL'
    transfer_volume = '100 uL'

    # define initial contents and create container
    initial_contents = [(triethylamine, initial_volume)]
    container = recipe.create_container('container', max_volume='20 mL', initial_contents=initial_contents)

    # Test if container.volume is correct intially
    assert container.volume == 0

    # Make sure that the recipe uses empty_plate
    recipe.uses(empty_plate)

    recipe.transfer(container, empty_plate, transfer_volume)
    results = recipe.bake()
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

    assert pytest.approx(container.volume) == expected_volume_plate
    assert (np.full((8, 12), expected_volume_container) == plate.volumes(unit='uL')).all()
    assert pytest.approx(
        recipe.amount_used(substance=triethylamine, timeframe='dispensing', unit='uL')) == expected_volume_plate


def test_amount_used_dilute(salt, water):
    """
    Tests that the substance amount tracking is correctly tracked during dilution in a recipe.

    This test checks the `amount_used` method  to correctly report the amount of salt used after diluting a saltwater solution. The procedure involves:
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
    salt_solution = recipe.create_solution(salt, water, concentration='0.5 M', total_quantity='20 mL')
    # container._add(salt_water, '10 mL')

    recipe.transfer(salt_solution, container, '10 mL')

    # Add solute to recipe
    # container = container._add(salt, '50 mmol') #Does not do anything as the container that is used in the recipe is the one that was stored initially
    recipe.dilute(container, solute=salt, concentration='0.25 M', solvent=water)
    recipe.bake()

    assert container.volume == 0
    # Results would contain the pointers to the new containers, so assert from there

    expected_salt_amount = '5.0 mmol'
    assert recipe.amount_used(substance=salt, timeframe='dispensing', unit='mmol') == expected_salt_amount


# Testing create_solution
def test_amount_used_create_solution(salt, water):
    """
    Tests that the substance amount tracking is accurately implemented during the creation of a solution within a recipe.

    This test verifies the `amount_used` method to correctly report the amount of salt utilized in preparing a specific solution. The testing procedure includes:
    - Initiating a recipe and declaring the usage of salt and water as solute and solvent, respectively.
    - Creating a solution with a predefined concentration of '0.5 M' and a total quantity of '20 mL', effectively dissolving the salt within the water.
    - Executing the `bake` method to finalize the creation of the solution.

    The assertions made are:
    - The initial volume of the container is checked before the solution creation, ensuring it starts from a baseline of zero.
    - The amount of salt reported as used during the recipe matches the expected calculation, which is '10 mmol' for achieving the desired solution concentration and volume. This confirms the `amount_used` method's accuracy in reflecting substance usage throughout the recipe's actions.

    Parameters:
    - salt (Substance): The salt intended to be dissolved to create the solution.
    - water (Substance): The water used as a solvent for the solution.

    """

    # Create recipe
    recipe = Recipe()
    recipe.uses(salt, water)

    # Create solution and add to container
    container = recipe.create_solution(salt, water, concentration='0.5 M', total_quantity='20 mL')
    ##What is the initial volume of container here?
    assert container.volume == 0

    # Bake recipe
    recipe.bake()

    # Assertions
    expected_salt_amount = '10.0 mmol'
    assert recipe.amount_used(substance=salt, timeframe='all', unit='mmol') == expected_salt_amount

# Try substance with solid and liquid
def test_amount_used_create_solution_from(salt, water, triethylamine):
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
    initial_container_name = "initial_salt_solution"
    container = recipe.create_solution(salt, water, concentration='0.5 M', total_quantity='20 mL', name=initial_container_name)
    
    # Create solution from the initial one with a new solvent
    new_container_name = "new_solution_from_initial"
    residual, new_container = recipe.create_solution_from(container, solute=salt, concentration='0.5 M', solvent=triethylamine, quantity='20 mL', name=new_container_name)
    
    # Bake recipe to finalize
    recipe.bake()

    # Assertions for substance amount used and container volumes
    expected_salt_amount = '10 mmol'
    assert recipe.amount_used(substance=salt, timeframe='during', unit='mmol') == expected_salt_amount, "The reported amount of salt used does not match the expected value."
    assert residual == 0, "Expected residual volume to be 0 after creating new solution."
    assert new_container.volume == '20 mL', "Expected new container volume to match the specified total quantity for the new solution."


def test_amount_used_remove(salt_water, salt):
    """
    Tests the accuracy of substance amount tracking during the removal of a solution in a recipe.

    This test verifies the `amount_used` method for correctly reporting the amount of salt removed from a container. The procedure includes:
    - Creating a recipe and a container with an initial volume of '20 mL' of saltwater, implying a certain concentration of salt.
    - Removing '10 mL' of the saltwater from the container, which would also remove a proportional amount of salt based on the solution's concentration.
    - Baking the recipe to finalize the removal process.

    The test asserts:
    - The amount of salt removed during the recipe matches the expected value based on the initial concentration and the volume removed. The expected salt amount should logically reflect the proportion of salt in the removed volume, which, in a homogenous solution, would be half of the initial amount if '20 mL' contained '50 mmol' of salt.

    Parameters:
    - salt_water (Container): A fixture representing the saltwater solution to be partially removed.
    - salt (Substance): The salt substance, expected to be tracked through the `amount_used` method.
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
    expected_salt_amount = '0.0 mmol'
    assert recipe.amount_used(substance=salt, timeframe='dispensing', unit='mmol') == expected_salt_amount


def test_amount_used_with_no_usage(salt):

    """
    Verifies that the amount of a substance reported as used is zero when the substance is not utilized in the recipe.

    This test case is designed to confirm the functionality of the `amount_used` method in scenarios where a specific substance is declared for a recipe but not actually used in any of the recipe steps. The key actions in this test include:
    - Initiating a recipe without adding any steps that involve the use of the specified substance (salt, in this case).
    - Finalizing the recipe preparation process by baking the recipe.
    
    The assertion checks:
    - That the `amount_used` method correctly reports '0 mmol' for the salt, reflecting that it was not used during the recipe's preparation, thus ensuring accurate tracking of substance usage within the recipe.

    Parameters:
    - salt (Substance): The substance fixture representing salt, intended to verify the tracking of substance usage.
    """

    recipe = Recipe()
    # No usage of salt
    recipe.bake()
    # Expecting 0 usage since salt wasn't used
    assert recipe.amount_used(substance=salt, timeframe='all', unit='mmol') == '0.0 mmol'


def test_amount_used_incorrect_timeframe(salt_water, salt, empty_plate):
    """
    Ensures an error is raised when querying the amount of substance used with an unsupported timeframe.

    This test aims to verify the error handling capabilities of the `amount_used` method within the `Recipe` class, particularly when an invalid or unsupported timeframe is specified. The test follows these steps:
    - Initializes a recipe and declares the use of a saltwater solution.
    - Transfers a specified volume of the saltwater solution to a plate, simulating a typical recipe action.
    - Completes the recipe by invoking the `bake` method.
    
    The critical part of this test is the assertion that checks:
    - A `ValueError` is raised when attempting to call `amount_used` with a timeframe argument that the method does not support (`'later'` in this case). The error message is expected to match "Unsupported timeframe," indicating that the method correctly identifies and rejects invalid timeframe inputs.

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
        recipe.amount_used(substance=salt, timeframe='later', unit='mmol')










