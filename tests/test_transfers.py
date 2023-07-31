from PyPlate import Plate, Substance, Container, Generic96WellPlate
import pytest
from copy import deepcopy
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
    solution3, solution4 = solution2.transfer(solution1, '10 mL')
    # original solutions should be unchanged
    assert solution2.volume == 100 and solution1.volume == 100
    # 10 mL of water and 5 moles of salt should have been transferred
    assert solution3.volume == 90 and solution4.volume == 110
    assert solution3.contents[water] == 90 and solution3.contents[salt] == 45
    assert solution4.contents[water] == 10 and solution4.contents[salt] == 5


def test_add_to_slice(plate1, salt):
    plate3 = plate1[:].add(salt, '10 mol')
    assert numpy.array_equal(plate3.moles(salt), numpy.full(plate3.wells.shape, 10))
    assert numpy.array_equal(plate1.moles(salt), numpy.zeros(plate1.wells.shape))


def test_transfer_to_slice(plate1, solution1):
    solution3, plate3 = plate1[:].transfer(solution1, '1 mL')
    # 1 mL should have been transferred to each well in the plate
    assert plate3.volume() == plate3[:].size
    assert numpy.all(numpy.vectorize(lambda elem: elem.volume == 1)(plate3.wells))
    # Original solution and plate should be unchanged
    assert solution1.volume == 100
    assert plate1.volume() == 0
