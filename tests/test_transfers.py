from PyPlate import Plate, Substance, Container, Generic96WellPlate
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
    return Generic96WellPlate('plate1', 50_000)


@pytest.fixture
def plate2() -> Plate:
    return Generic96WellPlate('plate2', 50_000)


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
    container = Container('container', max_volume=10_000).add(frm=salt, how_much='10 mol')
    # container should contain 10 moles of salt
    assert salt in container.contents and container.contents[salt] == 10

    container1 = Container('container', max_volume=10_000).add(frm=water, how_much='10 mL')
    # container1 should contain 10 mL of water and its volume should be 10 mL
    assert water in container1.contents and container1.contents[water] == 10
    assert container1.volume == 10

    container2 = container1.add(salt, '5 mol')
    # container2's volume shouldn't be changed by adding salt
    assert container2.volume == 10

    container3 = container2.add(water, '5 mL')
    # water should stack in the contents and the volume should be updated
    assert container3.contents[water] == 15 and container3.volume == 15

    # the original container should be unchanged
    assert container.volume == 0 and container.contents[salt] == 10


def test_transfer_between_containers(solution1, solution2, water, salt):
    """
    Tests transferring from one container to another.
    """
    solution3, solution4 = solution2.transfer(solution1, '10 mL')
    # original solutions should be unchanged
    assert solution2.volume == 100 and solution1.volume == 100
    # 10 mL of water and 5 moles of salt should have been transferred
    assert solution3.volume == 90 and solution4.volume == 110
    assert solution3.contents[water] == 90 and solution3.contents[salt] == 45
    assert solution4.contents[water] == 10 and solution4.contents[salt] == 5


def test_add_to_slice(plate1, salt):
    """
    Tests adding a substance to each well in a slice.
    """
    plate3 = plate1[:].add(salt, '10 mol')
    # 10 moles of salt should be in each well
    assert numpy.array_equal(plate3.moles(salt), numpy.full(plate3.wells.shape, 10))
    # Original plate should be unchanged
    assert numpy.array_equal(plate1.moles(salt), numpy.zeros(plate1.wells.shape))


def test_transfer_to_slice(plate1, solution1):
    """
    Tests transferring from a container to each well in a slice.
    """
    solution3, plate3 = plate1[:].transfer(solution1, '1 mL')
    # 1 mL should have been transferred to each well in the plate
    assert plate3.volume() == plate3[:].size
    assert numpy.all(numpy.vectorize(lambda elem: elem.volume == 1)(plate3.wells))
    # Original solution and plate should be unchanged
    assert solution1.volume == 100
    assert plate1.volume() == 0


def test_transfer_between_slices(plate1, plate2, solution1, solution2):
    """
    Tests transfer from the wells in one slice to the wells in another.
    """
    left_over_solution, plate3 = plate1[1, 1].transfer(solution1, '10 mL')
    initial_volumes = plate3.volumes().copy()
    # 10 mL of solution should in the first well
    assert initial_volumes[0, 0] == 10
    plate4, _ = plate3[8:].transfer_slice(plate3[1, 1], '0.1 mL')
    volumes = plate4.volumes()
    intended_result_volumes = numpy.zeros(volumes.shape)
    # Solution should have been transferred between
    #   the first well and the last row
    intended_result_volumes[0, 0] = 10 - 0.1 * 12
    intended_result_volumes[7:] = 0.1
    assert numpy.array_equal(volumes, intended_result_volumes)
    # Plate3 should not have been modified
    assert numpy.array_equal(initial_volumes, plate3.volumes())

    # Plate with first row containing 1mL of solution1
    left_over_solution1, plate5 = plate1[:1].transfer(solution1, '1 mL')
    # Plate with last row containing 2mL of solution2
    left_over_solution2, plate6 = plate2[8:].transfer(solution2, '2 mL')
    # Expected starting volumes
    assert plate5.volume() == 12 and plate6.volume() == 24
    plate7, plate8 = plate6[8:].transfer_slice(plate5[:1], '1 mL')
    # From plate should be empty
    assert plate7.volume() == 0
    intended_result_volumes = numpy.zeros(plate8[:].shape)
    intended_result_volumes[7:] = 3
    # Last row should have 3 mL in each well
    assert numpy.array_equal(intended_result_volumes, plate8.volumes())


def test_transfer_from_slice(plate1, solution1):
    """
    Tests transferring from each well in a slice to a container.
    """
    solution3, plate3 = plate1[:].transfer(solution1, '1 mL')
    destination_solution = Container('destination', 100)
    plate4, destination_solution = destination_solution.transfer_slice(plate3, '0.5 mL')
    # Original plate should have 1 mL in each well
    assert numpy.array_equal(plate3.volumes(), numpy.ones(plate3[:].shape))
    # Destination container should have 0.5 mL for each well
    assert destination_solution.volume == 0.5 * plate3[:].size
    # Source wells should all have 0.5 mL
    assert numpy.array_equal(plate4.volumes(), numpy.ones(plate4[:].shape) * 0.5)
