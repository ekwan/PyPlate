from PyPlate import Plate, Substance, Container, Unit
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
    return Plate('plate1', 50_000)


@pytest.fixture
def plate2() -> Plate:
    return Plate('plate2', 50_000)


@pytest.fixture
def solution1(water, salt) -> Container:
    return Container('sol1', max_volume=1_000, initial_contents=[(water, '100 mL'), (salt, '50 mol')])


@pytest.fixture
def solution2(dmso, sodium_sulfate) -> Container:
    return Container('sol2', max_volume=1_000, initial_contents=[(dmso, '100 mL'), (sodium_sulfate, '50 mol')])


def test_add_to_container(salt, water):
    """
    Tests adding a substance to a container.
    """
    container = Container('container', max_volume=10)
    container = Container.add(salt, container, '10 mol')

    # container should contain 10 moles of salt
    assert salt in container.contents and Unit.convert_from_storage(container.contents[salt], 'mol') == 10

    container1 = Container('container', max_volume=20)
    container1 = Container.add(water, container1, '10 mL')
    # container1 should contain 10 mL of water and its volume should be 10 mL
    assert water in container1.contents and Unit.convert_from_storage(container1.contents[water], 'mL') == 10
    assert Unit.convert_from_storage(container1.volume, 'mL') == 10

    container2 = Container.add(salt, container1, '5 mol')
    # container2's volume shouldn't be changed by adding salt
    assert Unit.convert_from_storage(container2.volume, 'mL') == 10

    container3 = Container.add(water, container2, '5 mL')
    # water should stack in the contents and the volume should be updated
    assert Unit.convert_from_storage(container3.contents[water], 'mL') == 15 and \
           Unit.convert_from_storage(container3.volume, 'mL') == 15

    # the original container should be unchanged
    assert container.volume == 0 and \
           Unit.convert_from_storage(container.contents[salt], 'mol') == 10


def test_transfer_between_containers(solution1, solution2, water, salt):
    """
    Tests transferring from one container to another.
    """
    solution3, solution4 = Container.transfer(solution1, solution2, '10 mL')  # solution2.transfer(solution1, '10 mL')
    # original solutions should be unchanged
    assert Unit.convert_from_storage(solution2.volume, 'mL') == 100 and \
           Unit.convert_from_storage(solution1.volume, 'mL') == 100
    # 10 mL of water and 5 moles of salt should have been transferred
    assert Unit.convert_from_storage(solution3.volume, 'mL') == 90 and \
           Unit.convert_from_storage(solution4.volume, 'mL') == 110
    assert Unit.convert_from_storage(solution3.contents[water], 'mL') == 90 and \
           Unit.convert_from_storage(solution3.contents[salt], 'mol') == 45
    assert Unit.convert_from_storage(solution4.contents[water], 'mL') == 10 and \
           Unit.convert_from_storage(solution4.contents[salt], 'mol') == 5


def test_add_to_slice(plate1, salt):
    """
    Tests adding a substance to each well in a slice.
    """
    plate3 = Plate.add(salt, plate1[:], '10 mol')
    # 10 moles of salt should be in each well
    assert numpy.array_equal(plate3.moles(salt), numpy.full(plate3.wells.shape, 10))
    # Original plate should be unchanged
    assert numpy.array_equal(plate1.moles(salt), numpy.zeros(plate1.wells.shape))


def test_transfer_to_slice(plate1, solution1):
    """
    Tests transferring from a container to each well in a slice.
    """
    solution3, plate3 = Plate.transfer(solution1, plate1[:], '1 mL')  # plate1[:].transfer(solution1, '1 mL')
    # 1 mL should have been transferred to each well in the plate
    assert plate3.volume() == plate3[:].size * 1000         # volume() is in uL
    assert numpy.all(numpy.vectorize(lambda elem: Unit.convert_from_storage(elem.volume, 'mL') == 1)(plate3.wells))
    # Original solution and plate should be unchanged
    assert Unit.convert_from_storage(solution1.volume, 'mL') == 100
    assert plate1.volume() == 0


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
    destination_solution = Container('destination', 100)
    # plate4, destination_solution = destination_solution.transfer_slice(plate3, '0.5 mL')
    plate4, destination_solution = Container.transfer(plate3, destination_solution, '0.5 mL')
    # Original plate should have 1 mL in each well
    assert numpy.array_equal(plate3.volumes(), numpy.ones(plate3[:].shape) * 1000)
    # Destination container should have 0.5 mL for each well
    assert destination_solution.volume == Unit.convert_to_storage(0.5 * plate3[:].size, 'mL')
    # Source wells should all have 0.5 mL
    assert numpy.array_equal(plate4.volumes(), numpy.ones(plate4[:].shape) * 0.5 * 1000)
