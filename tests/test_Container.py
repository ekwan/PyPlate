import pytest
from pyplate import Container
from pyplate.pyplate import config, Unit


def test_make_Container(water, salt):
    """

    Tests that `Container` constructor checks the type of all arguments.

    It checks the following scenarios:
    - Argument types are correctly validated.

    """
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
    with pytest.raises(TypeError, match="Element in initial_contents must be"):
        Container('container', '1 L', [(water, 1), (salt, 1)])


def test_Container_transfer(water, salt, water_stock, salt_water):
    """

    Tests if transfers between `Container`s works properly.

    """
    # Argument types checked
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
    assert container1.volume == Unit.convert(water, '90 mL', config.volume_storage_unit) \
           + Unit.convert(salt, '45 mmol', config.volume_storage_unit)
    assert container1.contents[water] == Unit.convert(water, '90 mL', config.moles_storage_unit)
    assert container1.contents[salt] == Unit.convert(salt, '45 mmol', config.moles_storage_unit)
    assert container2.volume == Unit.convert(water, '20 mL', config.volume_storage_unit)\
           + Unit.convert(salt, '5 mmol', config.volume_storage_unit)
    assert salt in container2.contents and container2.contents[salt] == \
           Unit.convert(salt, '5 mmol', config.moles_storage_unit)
    assert container2.contents[water] == pytest.approx(Unit.convert(water, '20 mL', config.moles_storage_unit))

    # Original containers should be unchanged.
    assert initial_hashes == (hash(water_stock), hash(salt_water))

    salt_stock = Container('salt stock', initial_contents=[(salt, '10 g')])
    container1, container2 = Container.transfer(salt_stock, salt_water, '1 g')
    assert container2.contents[salt] == \
           pytest.approx(salt_water.contents[salt] + Unit.convert(salt, '1 g', config.moles_storage_unit))


def test_create_stock_solution(water, salt, salt_water):
    """

    Tests if transfers between `Container`s works properly.

    """
    # Argument types checked
    with pytest.raises(TypeError, match=r'Solute\(s\) must be a Substance'):
        Container.create_solution('salt', water, concentration='0.5 M', total_quantity='100 mL')
    with pytest.raises(TypeError, match=r'Concentration\(s\) must be a str'):
        Container.create_solution(salt, water, concentration=.5, total_quantity='100 mL')
    with pytest.raises(TypeError, match='Solvent must be a Substance'):
        Container.create_solution(salt, 'water', concentration='0.5 M', total_quantity='100 mL')
    with pytest.raises(TypeError, match='Total quantity must be a str'):
        Container.create_solution(salt, water, concentration='0.5 M', total_quantity=100.0)

    stock = Container.create_solution(salt, water, concentration='0.5 M', total_quantity='100 mL')
    # stock should have 100 mL of water and 50 mmol of salt
    assert water in stock.contents and salt in stock.contents
    assert stock.volume == Unit.convert_to_storage(100, 'mL')
    assert stock.contents[salt] == pytest.approx(salt_water.contents[salt])


def test__self_add(water):
    """

    Tests _self_add method of Container.

    It checks the following scenarios:
    - The argument types are correctly validated.
    - The substance is correctly added to the container.
    - The method raises a ValueError if the substance cannot be added to the container.

    """

    container = Container('container', max_volume='5 mL')

    # Argument types checked
    with pytest.raises(TypeError, match='Source must be a Substance'):
        container._self_add('water', '5 mL')
    with pytest.raises(TypeError, match='Quantity must be a str'):
        container._self_add(water, 5)

    # Use the _self_add method to add the substance to the container
    container._self_add(water, '5 mL')

    # Check if the substance was correctly added to the container
    assert water in container.contents
    assert pytest.approx(container.contents[water]) == Unit.convert(water, '5 mL', config.moles_storage_unit)
    assert pytest.approx(container.volume) == Unit.convert_to_storage(5, 'mL')

    # Try to add more substance than the container can hold
    with pytest.raises(ValueError, match='Exceeded maximum volume'):
        container._self_add(water, '10 mL')


def test__transfer(water):
    """

    Tests _transfer method of Container.

    It checks the following scenarios:
    - The argument types are correctly validated.
    - The substance is correctly transferred to the second container.
    - The method raises a ValueError if there is not enough substance in the source container.
    - The method raises a ValueError if the second container cannot hold the transferred substance.

    """

    # Argument types checked
    container1 = Container('container1', '10 mL')
    container2 = Container('container2', '10 mL')
    with pytest.raises(TypeError, match='Invalid source type'):
        container1._transfer(1, '10 mL')
    with pytest.raises(TypeError, match='Quantity must be a str'):
        container1._transfer(container2, 5)

    for unit in ['mL', 'mg', 'mmol']:
        container1 = Container('container1', '10 mL', initial_contents=[(water, f"5 {unit}")])
        container2 = Container('container2', '10 mL')
        # Use the _transfer method to transfer the substance from the first to the second container
        container1, container2 = container2._transfer(container1, f"2 {unit}")

        # Check if the substance was correctly transferred
        assert water in container2.contents
        assert (pytest.approx(container2.contents[water]) ==
                Unit.convert(water, f"2 {unit}", config.moles_storage_unit))
        assert (pytest.approx(container2.volume) ==
                Unit.convert(water, f"2 {unit}", config.volume_storage_unit))

        # Check if the volume of the first container was correctly reduced
        assert (pytest.approx(container1.contents[water]) ==
                Unit.convert(water, f"3 {unit}", config.moles_storage_unit))
        assert (pytest.approx(container1.volume) ==
                Unit.convert(water, f"3 {unit}", config.volume_storage_unit))

    container1 = Container('container1', '10 mL', initial_contents=[(water, '5 mL')])
    container2 = Container('container2', '10 mL')

    # Try to transfer more substance than the first container holds
    with pytest.raises(ValueError, match='Not enough mixture left in source container'):
        container2._transfer(container1, '10 mL')

    container1 = Container('container1', '20 mL', initial_contents=[(water, '20 mL')])
    # Try to transfer more substance than the second container can hold
    with pytest.raises(ValueError, match='Exceeded maximum volume'):
        container2._transfer(container1, '20 mL')


def test_get_concentration(water, salt, dmso):
    """

    Tests get_concentration method of Container.

    It checks the following scenarios:
    - The argument types are correctly validated.
    - The method returns the correct concentration of the substance in the container.
    - The method raises a ValueError if the substance is not in the container.

    """

    # Argument types checked
    container = Container('container', '10 mL')
    with pytest.raises(TypeError, match='Solute must be a Substance'):
        container.get_concentration('water')
    with pytest.raises(TypeError, match='Units must be a str'):
        container.get_concentration(water, 1)

    # Check if the method returns the correct concentration of the substance in the container
    for value in [0.1, 0.5, 1.0]:
        stock = Container.create_solution(salt, water, concentration=f"{value} M", total_quantity='100 mL')
        assert stock.get_concentration(salt) == pytest.approx(value, abs=1e-3)

    ratio = stock.contents[salt] / sum(stock.contents.values())
    assert pytest.approx(ratio, abs=1e-3) == stock.get_concentration(salt, 'mol/mol')
    # Try to get the concentration of a substance that is not in the container
    assert stock.get_concentration(dmso) == 0


def test_create_solution_from(water, salt):
    # Create a stock solution of 1 M salt water
    stock = Container.create_solution(salt, water, concentration='1 M', total_quantity='100 mL')

    # Create a solution of 0.5 M salt water from the stock solution
    stock, solution = Container.create_solution_from(stock, salt,'0.5 M', water, '50 mL')

    # Should contain 25 mmol of salt and have a total volume of 50 mL
    assert pytest.approx(Unit.convert(salt, '25 mmol', config.moles_storage_unit)) == solution.contents[salt]
    assert pytest.approx(Unit.convert(water, '50 mL', config.volume_storage_unit)) == solution.volume
    assert pytest.approx(Unit.convert_from_storage(solution.volume, 'mL')) == 50.0

    # stock should have a volume of 75 mL and 75 mmol of salt
    # Try to create a solution with more volume than the source container holds
    with pytest.raises(ValueError, match='Not enough mixture left in source container'):
        Container.create_solution_from(stock, salt, '1 M', water, '100 mL')

def test_create_solution(water, salt, sodium_sulfate):

    # create solution with just one solute
    simple_solution = Container.create_solution(salt, water, concentration='1 M', total_quantity='100 mL')

    water_container = Container('water', initial_contents=[(water, '100 mL')])

    # create solution with multiple solutes
    conc_quant_solution = Container.create_solution([salt, sodium_sulfate], water,
                                                    concentration=['1 M', '1 M'],
                                                    quantity=['5.84428 g', '14.204 g'])
    conc_total_quant_solution = Container.create_solution([salt, sodium_sulfate], water,
                                                          concentration=['1 M', '1 M'],
                                                          total_quantity='100 mL')

    qaunt_total_quant_solution = Container.create_solution([salt, sodium_sulfate], water,
                                                           quantity=['5.84428 g', '14.204 g'],
                                                           total_quantity='100 mL')

    # create solvent container
    water_container = Container('water', initial_contents=[(water, '100 mL')])

    # create solvent container with solute in it
    invalid_solvent_container = Container.create_solution(salt, water, concentration='1 M', total_quantity='100 mL')


    ## verify simple solution
    # verify solute amount
    assert (pytest.approx(Unit.convert_from(salt, 100, 'mmol', config.moles_storage_unit)) ==
            simple_solution.contents[salt])
    # verify concentration
    assert simple_solution.get_concentration(salt) == pytest.approx(1)
    # verify total volume
    assert (pytest.approx(Unit.convert_from(water, 100, 'mL', config.volume_storage_unit)) ==
            simple_solution.volume)

    ## verify conc_quant_solution
    # verify solute amounts
    assert (pytest.approx(Unit.convert_from(salt, 5.84428, 'g', config.moles_storage_unit)) ==
            conc_quant_solution.contents[salt])
    assert (pytest.approx(Unit.convert_from(sodium_sulfate, 14.204, 'g', config.moles_storage_unit)) ==
            conc_quant_solution.contents[sodium_sulfate])
    # verify concentration
    assert conc_quant_solution.get_concentration(salt) == pytest.approx(1)
    assert conc_quant_solution.get_concentration(sodium_sulfate) == pytest.approx(1)
    # verify total volume
    assert (pytest.approx(Unit.convert_from(water, 100, 'mL', config.volume_storage_unit)) ==
            conc_quant_solution.volume)

    ## verify conc_total_quant_solution
    # verify solute amounts
    assert (pytest.approx(Unit.convert_from(salt, 5.84428, 'g', config.moles_storage_unit)) ==
            conc_total_quant_solution.contents[salt])
    assert (pytest.approx(Unit.convert_from(sodium_sulfate, 14.204, 'g', config.moles_storage_unit)) ==
            conc_total_quant_solution.contents[sodium_sulfate])
    # verify concentration
    assert conc_total_quant_solution.get_concentration(salt) == pytest.approx(1)
    assert conc_total_quant_solution.get_concentration(sodium_sulfate) == pytest.approx(1)
    # verify total volume
    assert (pytest.approx(Unit.convert_from(water, 100, 'mL', config.volume_storage_unit)) ==
            conc_total_quant_solution.volume)

    ## verify qaunt_total_quant_solution
    # verify solute amounts
    assert (pytest.approx(Unit.convert_from(salt, 5.84428, 'g', config.moles_storage_unit)) ==
            qaunt_total_quant_solution.contents[salt])
    assert (pytest.approx(Unit.convert_from(sodium_sulfate, 14.204, 'g', config.moles_storage_unit)) ==
            qaunt_total_quant_solution.contents[sodium_sulfate])
    # verify concentration
    assert qaunt_total_quant_solution.get_concentration(salt) == pytest.approx(1)
    assert qaunt_total_quant_solution.get_concentration(sodium_sulfate) == pytest.approx(1)
    # verify total volume
    assert (pytest.approx(Unit.convert_from(water, 100, 'mL', config.volume_storage_unit)) ==
            qaunt_total_quant_solution.volume)


    # TODO: Update with actual error
    with pytest.raises(ValueError, match="Solution is impossible to create."):
        # create solution with solute in solvent container
        invalid_container_solution = Container.create_solution([salt, sodium_sulfate], invalid_solvent_container,
                                                               concentration='1 M', quantity=['1 g', '0.5 g'])

    with pytest.raises(ValueError, match="Solution is impossible to create."):
        # invalid quantity of solute
        container_solution = Container.create_solution([salt, sodium_sulfate], water_container,
                                                       concentration=['1 M', '1 M'],
                                                       quantity=['1 g', '0.5 g'])
