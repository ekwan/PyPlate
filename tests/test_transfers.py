import pytest
import numpy
from pyplate import Plate, Container
from pyplate.pyplate import Unit, config


@pytest.fixture
def plate1() -> Plate:
    return Plate('plate1', '50 mL')


@pytest.fixture
def plate2() -> Plate:
    return Plate('plate2', '50 mL')


@pytest.fixture
def solution1(water, salt) -> Container:
    return Container('sol1', initial_contents=[(water, '100 mL'), (salt, '50 mmol')])


@pytest.fixture
def solution2(dmso, sodium_sulfate) -> Container:
    return Container('sol2', initial_contents=[(dmso, '100 mL'), (sodium_sulfate, '50 mmol')])


def test_transfer_between_containers(solution1, solution2, water, salt, dmso, sodium_sulfate):
    """
    Tests transferring from one container to another.
    """
    # solution1 has 100mL of water and 50 nmol of solt
    # solution2 has 100mL of dmso and 50 nmol of sodium sulfate
    solution1_volume = 100 + Unit.convert(salt, '50 mmol', 'mL')
    solution2_volume = 100 + Unit.convert(sodium_sulfate, '50 mmol', 'mL')
    solution3, solution4 = Container.transfer(solution1, solution2, f"{solution1_volume*0.1} mL")
    # original solutions should be unchanged
    assert solution1.volume == Unit.convert_to_storage(solution1_volume, 'mL')
    assert solution2.volume == Unit.convert_to_storage(solution2_volume, 'mL')
    # 10 mL of water and 5 moles of salt should have been transferred
    assert solution3.get_volume(unit='mL') == solution1_volume * 0.9
    assert solution4.volume == Unit.convert_to_storage(solution2_volume + solution1_volume*0.1, 'mL')
    assert solution3.contents[water] == Unit.convert(water, '90 mL', config.moles_storage_unit)
    assert solution3.contents[salt] == Unit.convert(salt, '45 mmol', config.moles_storage_unit)
    assert solution4.contents[water] == pytest.approx(Unit.convert(water, '10 mL', config.moles_storage_unit))
    assert solution4.contents[salt] == Unit.convert(salt, '5 mmol', config.moles_storage_unit)


def test_transfer_to_slice(plate1, solution1, salt):
    """
    Tests transferring from a container to each well in a slice.
    """
    solution1_volume = 100 + Unit.convert(salt, '50 mmol', 'mL')
    to_transfer = round(solution1_volume / 100, 3)
    solution3, plate3 = Plate.transfer(solution1, plate1[:], f"{to_transfer} mL")
    # 1 mL of water should have been transferred to each well in the plate
    assert plate3.get_volume(unit='uL') == pytest.approx(plate3[:].size * 1000 * to_transfer, abs=3)  # volume() is in uL
    assert numpy.allclose(plate3.get_volumes(unit='mL'), numpy.ones(plate3.wells.shape) * to_transfer)
    # assert numpy.all(numpy.vectorize(lambda elem: abs(elem.volume - to_transfer) < epsilon)(plate3.wells))
    # Original solution and plate should be unchanged
    assert solution1.volume == Unit.convert_to_storage(solution1_volume, 'mL')
    assert plate1.get_volume() == 0

    solution4, plate4 = Plate.transfer(solution1, plate1[1, 1], f"{to_transfer} mL")
    assert plate4.get_volume() == pytest.approx(1000 * to_transfer)
    assert solution1.get_volume(unit='mL') - solution4.get_volume(unit='mL') == pytest.approx(to_transfer)


def test_transfer_between_slices(plate1, plate2, solution1, solution2):
    """
    Tests transfer from the wells in one slice to the wells in another.
    """
    left_over_solution, plate3 = Plate.transfer(solution1, plate1[1, 1], '10 mL')
    initial_volumes = plate3.get_volumes().copy()
    # 10 mL of solution should in the first well
    assert initial_volumes[0, 0] == 10 * 1000
    plate4, _ = Plate.transfer(plate3[1, 1], plate3[8:], '0.1 mL')
    volumes = plate4.get_volumes()
    intended_result_volumes = numpy.zeros(volumes.shape)
    # Solution should have been transferred between
    #   the first well and the last row
    intended_result_volumes[0, 0] = (10 - 0.1 * 12) * 1000
    intended_result_volumes[7:] = 0.1 * 1000
    assert numpy.array_equal(volumes, intended_result_volumes)
    # Plate3 should not have been modified
    assert numpy.array_equal(initial_volumes, plate3.get_volumes())

    # Plate with first row containing 1mL of solution1
    left_over_solution1, plate5 = Plate.transfer(solution1, plate1[:1], '1 mL')
    # Plate with last row containing 2mL of solution2
    left_over_solution2, plate6 = Plate.transfer(solution2, plate2[8:], '2 mL')
    # Expected starting volumes
    assert plate5.get_volume() == 12 * 1000 and plate6.get_volume() == 24 * 1000
    plate7, plate8 = Plate.transfer(plate5[:1], plate6[8:], '1 mL')
    # From plate should be empty
    assert plate7.get_volume() == 0
    intended_result_volumes = numpy.zeros(plate8[:].shape)
    intended_result_volumes[7:] = 3 * 1000
    # Last row should have 3 mL in each well
    assert numpy.array_equal(intended_result_volumes, plate8.get_volumes())


def test_transfer_from_slice(plate1, solution1):
    """
    Tests transferring from each well in a slice to a container.
    """
    # solution3, plate3 = plate1[:].transfer(solution1, '1 mL')
    solution3, plate3 = Plate.transfer(solution1, plate1[:], '1 mL')
    destination_solution = Container('destination', '100 mL')
    plate4, destination_solution = Container.transfer(plate3, destination_solution, '0.5 mL')
    # Original plate should have 1 mL in each well
    assert numpy.array_equal(plate3.get_volumes(), numpy.ones(plate3[:].shape) * 1000)
    # Destination container should have 0.5 mL for each well
    assert destination_solution.volume == Unit.convert_to_storage(0.5 * plate3[:].size, 'mL')
    # Source wells should all have 0.5 mL
    assert numpy.array_equal(plate4.get_volumes(), numpy.ones(plate4[:].shape) * 0.5 * 1000)

    plate4, destination_solution = Container.transfer(plate3[1, :], destination_solution, '0.5 mL')
    assert plate3.get_volume() - plate4.get_volume() == 500 * plate3.n_columns
