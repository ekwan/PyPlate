import pytest
from pyplate.pyplate import Recipe, Unit, Container, Plate
from pyplate import config
from tests.conftest import salt_water


def test_locked():
    recipe = Recipe()
    recipe.bake()
    with pytest.raises(RuntimeError, match="Recipe has already been baked"):
        recipe.bake()


def test_uses(salt_water):
    recipe = Recipe()
    recipe.uses(salt_water)
    index = recipe.indexes.get(salt_water, None)
    assert index is not None
    assert recipe.results[index] == salt_water

    with pytest.raises(ValueError, match="Something declared as used wasn't used"):
        _ = recipe.bake()

    recipe = Recipe()
    recipe.bake()
    with pytest.raises(RuntimeError, match="This recipe is locked"):
        recipe.uses(salt_water)


def test_transfer(salt_water):
    container = Container('container')
    recipe = Recipe()
    recipe.uses(salt_water, container)
    with pytest.raises(TypeError, match="Invalid source type"):
        recipe.transfer('1', container, '10 mL')
    with pytest.raises(TypeError, match="Invalid destination type"):
        recipe.transfer(salt_water, '1', '10 mL')
    with pytest.raises(TypeError, match="Volume must be a str"):
        recipe.transfer(salt_water, container, 1)
    recipe.transfer(salt_water, container, '10 mL')
    # Container should still be empty until we bake.
    assert container.volume == 0
    new_salt_water, container = recipe.bake()
    assert container.volume == Unit.convert_to_storage(10, 'mL')
    assert salt_water.volume - new_salt_water.volume == Unit.convert_to_storage(10, 'mL')

    with pytest.raises(RuntimeError, match="This recipe is locked"):
        recipe.transfer(salt_water, container, '10 mL')
    recipe = Recipe()
    plate = Plate('plate', max_volume_per_well='1 mL')
    recipe.uses(salt_water, plate)
    recipe.transfer(salt_water, plate, '5 uL')
    recipe.transfer(salt_water, plate[1,1], '1 uL')
    new_salt_water, new_plate = recipe.bake()
    assert salt_water.volume - new_salt_water.volume == pytest.approx(Unit.convert_to_storage(5*96+1, 'uL'))
    volumes = new_plate.volumes(unit='uL')
    assert volumes[0, 0] == 6
    assert volumes[0, 1] == 5

    container = Container('container')
    recipe = Recipe()
    recipe.uses(container, new_plate)
    recipe.transfer(new_plate[1, 1], container, '2 uL')
    recipe.transfer(new_plate[1:2, 1:2], container, '1 uL')
    container, new_plate2 = recipe.bake()
    assert container.volume == Unit.convert_to_storage(2 + 4, 'uL')
    assert new_plate.volume('uL') - new_plate2.volume('uL') == 2 + 4

def test_create_container(water, salt):
    recipe = Recipe()
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
    recipe.used = set(recipe.indexes.values())
    assert container3.volume == 0
    container, container2, container3, = recipe.bake()
    assert Unit.convert_to_storage(10, 'mL') + Unit.convert(salt, '5 mmol', config.volume_prefix) == container3.volume
    assert container3.contents.get(salt, None) == Unit.convert_to_storage(5, 'mmol')
