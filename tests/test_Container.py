import pytest
from pyplate.pyplate import Substance, Container, Unit
from pyplate import config


@pytest.fixture
def water() -> Substance:
    return Substance.liquid('H2O', mol_weight=18.0153, density=1)


@pytest.fixture
def salt() -> Substance:
    return Substance.solid('NaCl', 58.4428)


@pytest.fixture
def water_stock(water) -> Container:
    return Container('water', initial_contents=((water, '10 mL'),))


@pytest.fixture
def salt_water(water, salt) -> Container:
    return Container('salt water', initial_contents=((water, '100 mL'), (salt, '50 mmol')))


def test_make_Container(water, salt):
    # Argument types checked
    with pytest.raises(TypeError, match="Name must be a str"):
        Container(1)
    with pytest.raises(ValueError, match="Name must not be empty"):
        Container('')
    with pytest.raises(TypeError, match='Maximum volume must be a str'):
        Container('container', 1)
    with pytest.raises(ValueError, match="Value is not a valid float"):
        Container('container', 'max_volume L')
    with pytest.raises(ValueError, match="Maximum volume must be positive"):
        Container('container', '-1 L')
    with pytest.raises(ValueError, match="Maximum volume must be positive"):
        Container('container', '0 L')
    with pytest.raises(TypeError, match="Initial contents must be iterable"):
        Container('container', '1 L', 1)
    with pytest.raises(TypeError, match="Element in initial_contents must be"):
        Container('container', '1 L', [1])
    with pytest.raises(TypeError, match="Element in initial_contents must be"):
        Container('container', '1 L', [water, salt])


def test_Container_add(water):
    container = Container('container')
    with pytest.raises(TypeError, match='Source must be a Substance'):
        Container.add(1, container, '10 mL')
    with pytest.raises(TypeError, match='You can only use Container.add to add to a Container'):
        Container.add(water, 1, '10 mL')
    with pytest.raises(TypeError, match='Quantity must be a str'):
        Container.add(water, container, 1)

    result = Container.add(water, container, '10 mL')
    # 10 mL of water should have been added.
    assert isinstance(result, Container)
    assert result.volume == Unit.convert_to_storage(10, 'mL')
    assert water in result.contents and result.contents[water] == Unit.convert(water, '10 mL', config.moles_prefix)
    # Original should be unchanged
    assert container.volume == 0
    assert water not in container.contents


def test_Container_transfer(water, salt, water_stock, salt_water):
    with pytest.raises(TypeError, match='into a Container'):
        Container.transfer(1, 1, '10 mL')
    with pytest.raises(TypeError, match='Invalid source type'):
        Container.transfer(1, water_stock, '10 mL')
    with pytest.raises(TypeError, match='Quantity must be a str'):
        Container.transfer(salt_water, water_stock, 1)

    initial_hashes = hash(water_stock), hash(salt_water)
    # water_stock is 10 mL, salt_water is 100 mL and 50 mol
    container1, container2 = Container.transfer(salt_water, water_stock, '10 mL')
    # 10 mL of water and 5 mol of salt should have been transferred
    assert container1.volume == Unit.convert(water, '90 mL', config.volume_prefix)
    assert container1.contents[water] == Unit.convert(water, '90 mL', config.moles_prefix)
    assert container1.contents[salt] == Unit.convert(salt, '45 mmol', config.moles_prefix)
    assert container2.volume == Unit.convert(water, '20 mL', config.volume_prefix)
    assert salt in container2.contents and container2.contents[salt] == \
           Unit.convert(salt, '5 mmol', config.moles_prefix)
    assert container2.contents[water] == Unit.convert(water, '20 mL', config.moles_prefix)

    # Original containers should be unchanged.
    assert initial_hashes == (hash(water_stock), hash(salt_water))


def test_create_stock_solution(water, salt, salt_water):
    with pytest.raises(TypeError, match='Solute must be a Substance'):
        Container.create_stock_solution('salt', 0.5, water, '100 mL')
    with pytest.raises(TypeError, match='Concentration must be a float'):
        Container.create_stock_solution(salt, '0.5', water, '100 mL')
    with pytest.raises(TypeError, match='Solvent must be a Substance'):
        Container.create_stock_solution(salt, 0.5, 'water', '100 mL')
    with pytest.raises(TypeError, match='Volume must be a str'):
        Container.create_stock_solution(salt, 0.5, water, 100)

    stock = Container.create_stock_solution(salt, 0.5, water, '100 mL')
    assert water in stock.contents and salt in stock.contents
    assert stock.contents[water] == salt_water.contents[water]
    assert stock.contents[salt] == salt_water.contents[salt]
