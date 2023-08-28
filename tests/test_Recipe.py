import pytest
from pyplate.pyplate import Recipe
from tests.conftest import salt_water


@pytest.fixture
def recipe():
    return Recipe()


def test_uses(recipe, salt_water):
    recipe.uses(salt_water)
    index = recipe.indexes.get(salt_water, None)
    assert index is not None
    assert recipe.results[index] == salt_water


def test_create_container(recipe, salt):
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
