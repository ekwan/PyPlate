import pytest
from pyplate import Plate, Container, Recipe
from pyplate.pyplate import Unit, config
from tests.conftest import salt_water


def test_locked():
    """

    Ensures once a recipe is baked, it cannot be baked again.

    """
    recipe = Recipe()
    recipe.bake()
    with pytest.raises(RuntimeError, match="Recipe has already been baked"):
        recipe.bake()


def test_uses(salt_water):
    """

    Tests uses() for a Recipe.

    It checks the following scenarios:
    - The object is correctly added and used in the recipe.
    - The uses method cannot be called once the recipe is baked.
    - The recipe raises a ValueError if something declared as used wasn't actually used in the recipe.
    """
    recipe = Recipe()
    recipe.uses(salt_water)
    assert salt_water.name in recipe.results
    assert recipe.results[salt_water.name] == salt_water

    with pytest.raises(ValueError, match="Something declared as used wasn't used"):
        _ = recipe.bake()

    recipe = Recipe()
    recipe.bake()
    with pytest.raises(RuntimeError, match="This recipe is locked"):
        recipe.uses(salt_water)


def test_transfer(salt_water):
    """
    Tests the transfer method within a Recipe.

    It checks the following scenarios:
    - Argument types are correctly validated.
    - The volume of the destination container is correctly updated after a transfer.
    - The volume of the source container is correctly reduced after a transfer.
    - The transfer method cannot be called once the recipe is baked.
    - The volume of a Plate is correctly updated after a transfer.
    - The volume of a specific well in a Plate is correctly updated after a transfer.
    - The volume of a Container is correctly updated after multiple transfers from different wells in a Plate.
    """
    container = Container('container')
    recipe = Recipe()
    recipe.uses(salt_water, container)
    # Argument types checked
    with pytest.raises(TypeError, match="Invalid source type"):
        recipe.transfer('1', container, '10 mL')
    with pytest.raises(TypeError, match="Invalid destination type"):
        recipe.transfer(salt_water, '1', '10 mL')
    with pytest.raises(TypeError, match="Volume must be a str"):
        recipe.transfer(salt_water, container, 1)
    recipe.transfer(salt_water, container, '10 mL')
    # Container should still be empty until we bake.
    assert container.volume == 0
    results = recipe.bake()
    new_salt_water = results[salt_water.name]
    container = results[container.name]
    assert container.get_volume(unit='mL') == 10
    assert salt_water.get_volume(unit='mL') - new_salt_water.get_volume(unit='mL') == 10

    # transfer() cannot ba called once the recipe is baked.
    with pytest.raises(RuntimeError, match="This recipe is locked"):
        recipe.transfer(salt_water, container, '10 mL')
    recipe = Recipe()
    plate = Plate('plate', max_volume_per_well='1 mL')
    recipe.uses(salt_water, plate)
    recipe.transfer(salt_water, plate, '5 uL')
    recipe.transfer(salt_water, plate[1, 1], '1 uL')
    results = recipe.bake()
    new_salt_water = results[salt_water.name]
    new_plate = results[plate.name]
    # 5 uL transferred to 96 wells and 1 uL to one well.
    assert salt_water.get_volume(unit='uL') - new_salt_water.get_volume(unit='uL') == pytest.approx(5 * 96 + 1)
    volumes = new_plate.get_volumes(unit='uL')
    # plate[1, 1] should have 6 uL, all others 5 uL
    assert volumes[0, 0] == 6
    assert volumes[0, 1] == 5

    container = Container('container')
    recipe = Recipe()
    recipe.uses(container, new_plate)
    recipe.transfer(new_plate[1, 1], container, '2 uL')
    recipe.transfer(new_plate[1:2, 1:2], container, '1 uL')
    results = recipe.bake()
    container = results[container.name]
    new_plate2 = results[new_plate.name]
    # 2 uL from plate[1, 1] and 1 uL from four wells.
    assert container.get_volume('uL') == 2 + 4
    assert new_plate.get_volume('uL') - new_plate2.get_volume('uL') == 2 + 4


def test_create_container(water, salt):
    """

    Test create_container within a Recipe.

    It checks the following scenarios:
    - Argument types are correctly validated.
    - The container cannot be created once the recipe is baked.
    - The name of the container is set correctly.
    - The maximum volume of the container is set correctly.
    - The initial contents of the container are added only at bake.
    """

    recipe = Recipe()
    # Argument types checked
    with pytest.raises(TypeError, match='Name must be a str'):
        recipe.create_container(1)
    with pytest.raises(TypeError, match='Maximum volume must be a str'):
        recipe.create_container('container', max_volume=1.0)
    with pytest.raises(TypeError, match='Initial contents must be iterable'):
        recipe.create_container('container', '10 mL', 1)
    with pytest.raises(TypeError, match='Initial contents must be iterable'):
        recipe.create_container('container', '10 mL', 1)
    for contents in [1, (1,), (salt,), (salt, 1, 1)]:
        with pytest.raises(TypeError, match='Elements of initial_contents must be of the form'):
            recipe.create_container('container', '10 mL', [contents])
    with pytest.raises(TypeError, match='Containers can only be created from substances'):
        recipe.create_container('container', '10 mL', [(1, 1)])
    with pytest.raises(TypeError, match='Quantity must be a str'):
        recipe.create_container('container', '10 mL', [(salt, 1)])

    recipe = Recipe()
    recipe.bake()
    # cannot create_container once the recipe is baked.
    with pytest.raises(RuntimeError, match="This recipe is locked"):
        recipe.create_container('container')

    recipe = Recipe()
    # Name set correctly
    container = recipe.create_container('container')
    assert container.name == 'container'

    # Maximum volume set correctly
    container2 = recipe.create_container('container2', max_volume='10 mL')
    assert Unit.convert_to_storage(10, 'mL') == container2.max_volume

    # Initial contents added correctly only at bake
    container3 = recipe.create_container('container3', initial_contents=[(water, '10 mL'), (salt, '5 mmol')])
    recipe.used = set(recipe.results.keys())
    assert container3.volume == 0
    results = recipe.bake()
    container = results[container.name]
    container2 = results[container2.name]
    container3 = results[container3.name]
    assert 10 + Unit.convert(salt, '5 mmol', 'mL') == container3.get_volume(unit='mL')
    assert container3.contents.get(salt, None) == Unit.convert_to_storage(5, 'mmol')
