from pyplate import config
from pyplate.pyplate import Plate, Substance, Container, Unit
import pytest
import numpy


@pytest.fixture
def water() -> Substance:
    return Substance.liquid('H2O', mol_weight=18.0153, density=1)


@pytest.fixture
def salt() -> Substance:
    return Substance.solid('NaCl', 58.4428)


@pytest.fixture
def dmso() -> Substance:
    return Substance.liquid('DMSO', 78.13, 1.1004)


@pytest.fixture
def sodium_sulfate() -> Substance:
    return Substance.solid('Sodium sulfate', 142.04)


@pytest.fixture
def plate1() -> Plate:
    return Plate('plate1', '50 mL')


@pytest.fixture
def plate2() -> Plate:
    return Plate('plate2', '50 mL')


@pytest.fixture
def solution1(water, salt) -> Container:
    return Container('sol1', initial_contents=[(water, '100 mL'), (salt, '50 mol')])


@pytest.fixture
def solution2(dmso, sodium_sulfate) -> Container:
    return Container('sol2', initial_contents=[(dmso, '100 mL'), (sodium_sulfate, '50 mol')])


def test_add_to_container(salt, water):
    """
    Tests adding a substance to a container.
    """
    container = Container('container', max_volume='10 mL')
    container = Container.add(salt, container, '10 mol')

    # container should contain 10 moles of salt
    assert salt in container.contents and container.contents[salt] == Unit.convert(salt, '10 mol', config.moles_prefix)

    container1 = Container('container', max_volume='20 mL')
    container1 = Container.add(water, container1, '10 mL')
    # container1 should contain 10 mL of water and its volume should be 10 mL
    assert water in container1.contents
    assert container1.contents[water] == Unit.convert(water, '10 mL', config.moles_prefix)
    assert container1.volume == Unit.convert_to_storage(10, 'mL')

    container2 = Container.add(salt, container1, '5 mol')
    # container2's volume shouldn't be changed by adding salt
    assert container2.volume == Unit.convert_to_storage(10, 'mL')

    container3 = Container.add(water, container2, '5 mL')
    # water should stack in the contents and the volume should be updated
    assert container3.contents[water] == Unit.convert(water, '15 mL', config.moles_prefix)
    assert container3.volume == Unit.convert_to_storage(15, 'mL')

    # the original container should be unchanged
    assert container.volume == 0
    assert container.contents[salt] == Unit.convert(salt, '10 mol', config.moles_prefix)


def test_transfer_between_containers(solution1, solution2, water, salt):
    """
    Tests transferring from one container to another.
    """
    solution3, solution4 = Container.transfer(solution1, solution2, '10 mL')  # solution2.transfer(solution1, '10 mL')
    # original solutions should be unchanged
    assert solution1.volume == Unit.convert_to_storage(100, 'mL')
    assert solution2.volume == Unit.convert_to_storage(100, 'mL')
    # 10 mL of water and 5 moles of salt should have been transferred
    assert solution3.volume == Unit.convert_to_storage(90, 'mL')
    assert solution4.volume == Unit.convert_to_storage(110, 'mL')
    assert solution3.contents[water] == Unit.convert(water, '90 mL', config.moles_prefix)
    assert solution3.contents[salt] == Unit.convert(salt, '45 mol', config.moles_prefix)
    assert solution4.contents[water] == Unit.convert(water, '10 mL', config.moles_prefix)
    assert solution4.contents[salt] == Unit.convert(salt, '5 mol', config.moles_prefix)


def test_add_to_slice(plate1, salt):
    """
    Tests adding a substance to each well in a slice.
    """
    plate3 = Plate.add(salt, plate1[:], '10 mol')
    # 10 moles of salt should be in each well
    assert numpy.array_equal(plate3.moles(salt), numpy.full(plate3.wells.shape, 10))
    # Original plate should be unchanged
    assert numpy.array_equal(plate1.moles(salt), numpy.zeros(plate1.wells.shape))

    plate3 = Plate.add(salt, plate1[1, 1], '10 mol')
    expected_moles = numpy.zeros(plate3.wells.shape)
    expected_moles[0, 0] = 10
    assert numpy.array_equal(plate3.moles(salt), expected_moles)
    assert numpy.array_equal(plate1.moles(salt), numpy.zeros(plate1.wells.shape))


def test_transfer_to_slice(plate1, solution1):
    """
    Tests transferring from a container to each well in a slice.
    """
    solution3, plate3 = Plate.transfer(solution1, plate1[:], '1 mL')  # plate1[:].transfer(solution1, '1 mL')
    # 1 mL should have been transferred to each well in the plate
    assert plate3.volume() == plate3[:].size * 1000  # volume() is in uL
    assert numpy.all(numpy.vectorize(lambda elem: elem.volume == Unit.convert_to_storage(1, 'mL'))(plate3.wells))
    # Original solution and plate should be unchanged
    assert solution1.volume == Unit.convert_to_storage(100, 'mL')
    assert plate1.volume() == 0

    solution4, plate4 = Plate.transfer(solution1, plate1[1, 1], '1 mL')
    assert plate4.volume() == 1000
    assert solution1.volume - solution4.volume == Unit.convert_to_storage(1, 'mL')


def test_transfer_between_slices(plate1, plate2, solution1, solution2):
    """
    Tests transfer from the wells in one slice to the wells in another.
    """
    left_over_solution, plate3 = Plate.transfer(solution1, plate1[1, 1], '10 mL')
    initial_volumes = plate3.volumes().copy()
    # 10 mL of solution should in the first well
    assert initial_volumes[0, 0] == 10 * 1000
    plate4, _ = Plate.transfer(plate3[1, 1], plate3[8:], '0.1 mL')
    volumes = plate4.volumes()
    intended_result_volumes = numpy.zeros(volumes.shape)
    # Solution should have been transferred between
    #   the first well and the last row
    intended_result_volumes[0, 0] = (10 - 0.1 * 12) * 1000
    intended_result_volumes[7:] = 0.1 * 1000
    assert numpy.array_equal(volumes, intended_result_volumes)
    # Plate3 should not have been modified
    assert numpy.array_equal(initial_volumes, plate3.volumes())

    # Plate with first row containing 1mL of solution1
    left_over_solution1, plate5 = Plate.transfer(solution1, plate1[:1], '1 mL')
    # Plate with last row containing 2mL of solution2
    left_over_solution2, plate6 = Plate.transfer(solution2, plate2[8:], '2 mL')
    # Expected starting volumes
    assert plate5.volume() == 12 * 1000 and plate6.volume() == 24 * 1000
    plate7, plate8 = Plate.transfer(plate5[:1], plate6[8:], '1 mL')
    # From plate should be empty
    assert plate7.volume() == 0
    intended_result_volumes = numpy.zeros(plate8[:].shape)
    intended_result_volumes[7:] = 3 * 1000
    # Last row should have 3 mL in each well
    assert numpy.array_equal(intended_result_volumes, plate8.volumes())


def test_transfer_from_slice(plate1, solution1):
    """
    Tests transferring from each well in a slice to a container.
    """
    # solution3, plate3 = plate1[:].transfer(solution1, '1 mL')
    solution3, plate3 = Plate.transfer(solution1, plate1[:], '1 mL')
    destination_solution = Container('destination', '100 mL')
    # plate4, destination_solution = destination_solution.transfer_slice(plate3, '0.5 mL')
    plate4, destination_solution = Container.transfer(plate3, destination_solution, '0.5 mL')
    # Original plate should have 1 mL in each well
    assert numpy.array_equal(plate3.volumes(), numpy.ones(plate3[:].shape) * 1000)
    # Destination container should have 0.5 mL for each well
    assert destination_solution.volume == Unit.convert_to_storage(0.5 * plate3[:].size, 'mL')
    # Source wells should all have 0.5 mL
    assert numpy.array_equal(plate4.volumes(), numpy.ones(plate4[:].shape) * 0.5 * 1000)

    plate4, destination_solution = Container.transfer(plate3[1, :], destination_solution, '0.5 mL')
    assert plate3.volume() - plate4.volume() == 500 * plate3.n_columns
