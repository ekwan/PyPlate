
from pyplate.pyplate import Recipe, Container
import pytest

def test_amount_used(salt_water, salt):
    container = Container('container')
    substance = salt
    recipe = Recipe()
    recipe.uses(salt_water, container)
    recipe.transfer(salt_water, container, '10 mL')
    recipe.bake()
    assert recipe.amount_used(substance = salt, timeframe = 'before', unit = 'mmol') == '50 mmol'


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
    #uses to tell recipe about other containers
    recipe.uses(other_container)
    
    #Add solute and solvent to the create_solution method
    initial_contents = [(water, '10 mL')]

    #Implicit definition of container being used
    container = recipe.create_container('container','20 mL', initial_contents)

    #Transfer 5 mL from container to other_container
    recipe.transfer(container, other_container, '5 mL')

    
    recipe.bake()
    #Assertions
    step = recipe.steps[-1]

    print(step.frm)
    print(step.to)
    assert recipe.amount_used(substance = water, timeframe = 'before', unit = 'mL') == '10 mL'
    assert recipe.amount_used(substance = water, timeframe = 'during', unit = 'mL') == '5 mL'


def test_container_to_plate(triethylamine, empty_plate):
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
    
    #create_recipe
    recipe = Recipe()
    
    #define initial and transfer volumes
    initial_volume = '10 mL'
    transfer_volume = '100 uL'

    #define initial contents and create container
    initial_contents = [(triethylamine, initial_volume)]
    container = recipe.create_container('container', max_volume = '20 mL', initial_contents = initial_contents)

    #Test if container.volume is correct intially
    assert container.volume == 0

    #Make sure that the recipe uses empty_plate 
    recipe.uses(empty_plate)

    recipe.transfer( container, empty_plate, transfer_volume)
    results = recipe.bake()
    container = results[container.name]

    #Calculate expected volume
    expected_volume_plate = '400 uL'
    expected_volume_container = '400 uL'

    #Assertions
    step = recipe.steps[-1]

    print(step.frm)
    print(step.to)

    print("Assertions start here")
    
    assert container.volume == expected_volume_container
    assert empty_plate.volume == expected_volume_plate
    assert pytest.approx(recipe.amount_used(substance = triethylamine, timeframe = 'during', unit = 'uL')) == expected_volume_plate



def test_amount_used_dilute(salt_water, salt, water):
        
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
    
    #Using self defined container
    container = Container('container')

    #Create recipe
    recipe = Recipe()
    
    #container = recipe.create_container('container', '20 mL', [(salt_water, '10 mL')])

    #Define what the recipe uses
    recipe.uses(salt_water, container)
    #container._add(salt_water, '10 mL')

    recipe.transfer(salt_water, container, '10 mL')

    #Add solute to recipe
    #container = container._add(salt, '50 mmol') #Does not do anything as the container that is used in the recipe is the one that was stored initially
    recipe.dilute(container,solute=salt, concentration='0.5 M',solvent=water)
    recipe.bake()

    assert container.volume == 0 
    #Results would contain the pointers to the new containers, so assert from there

    expected_salt_amount = '50 mmol'
    assert recipe.amount_used(substance = salt, timeframe = 'during', unit = 'mmol') == expected_salt_amount


#Still under testing
def test_amount_used_with_no_usage(salt):

    recipe = Recipe()
    # No usage of salt
    recipe.bake()
    # Expecting 0 usage since salt wasn't used
    assert recipe.amount_used(substance=salt, timeframe='before', unit='mmol') == '0 mmol'

def test_amount_used_incorrect_timeframe(salt_water, salt):
    recipe = Recipe()
    recipe.uses(salt_water, Container('container'))
    recipe.transfer(salt_water, Container('another container'), '10 mL')
    recipe.bake()
    
    # Raising errors for unexpected timeframes
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        recipe.amount_used(substance=salt, timeframe='later', unit='mmol')

#Try substance with solid and liquid


