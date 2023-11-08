import pytest
from pyplate import Container
from pyplate.pyplate import config, Unit


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


def test_Container_transfer(water, salt, water_stock, salt_water):
    with pytest.raises(TypeError, match='into a Container'):
        Container.transfer(1, 1, '10 mL')
    with pytest.raises(TypeError, match='Invalid source type'):
        Container.transfer(1, water_stock, '10 mL')
    with pytest.raises(TypeError, match='Quantity must be a str'):
        Container.transfer(salt_water, water_stock, 1)

    initial_hashes = hash(water_stock), hash(salt_water)
    # water_stock is 10 mL, salt_water is 100 mL and 50 mmol
    salt_water_volume = Unit.convert_from_storage(salt_water.volume, 'mL')
    container1, container2 = Container.transfer(salt_water, water_stock, f"{salt_water_volume*0.1} mL")
    # 10 mL of water and 5 mol of salt should have been transferred
    assert container1.volume == Unit.convert(water, '90 mL', config.volume_prefix)\
           + Unit.convert(salt, '45 mmol', config.volume_prefix)
    assert container1.contents[water] == Unit.convert(water, '90 mL', config.moles_prefix)
    assert container1.contents[salt] == Unit.convert(salt, '45 mmol', config.moles_prefix)
    assert container2.volume == Unit.convert(water, '20 mL', config.volume_prefix)\
           + Unit.convert(salt, '5 mmol', config.volume_prefix)
    assert salt in container2.contents and container2.contents[salt] == \
           Unit.convert(salt, '5 mmol', config.moles_prefix)
    assert container2.contents[water] == pytest.approx(Unit.convert(water, '20 mL', config.moles_prefix))

    # Original containers should be unchanged.
    assert initial_hashes == (hash(water_stock), hash(salt_water))


def test_create_stock_solution(water, salt, salt_water):
    with pytest.raises(TypeError, match='Solute must be a Substance'):
        Container.create_solution('salt', water, concentration='0.5 M', total_quantity='100 mL')
    with pytest.raises(TypeError, match='Concentration must be a str'):
        Container.create_solution(salt, water, concentration=.5, total_quantity='100 mL')
    with pytest.raises(TypeError, match='Solvent must be a Substance'):
        Container.create_solution(salt, 'water', concentration='0.5 M', total_quantity='100 mL')
    with pytest.raises(TypeError, match='Total quantity must be a str'):
        Container.create_solution(salt, water, concentration='0.5 M', total_quantity=100.0)

    stock = Container.create_solution(salt, water, concentration='0.5 M', total_quantity='100 mL')
    assert water in stock.contents and salt in stock.contents
    assert stock.volume == Unit.convert_to_storage(100, 'mL')
    assert stock.contents[salt] == pytest.approx(salt_water.contents[salt])
