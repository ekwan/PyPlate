import pytest
import numpy
from pyplate.pyplate import Unit, Substance, Container, Plate


@pytest.fixture
def salt() -> Substance:
    return Substance.solid('NaCl', 58.4428)


@pytest.fixture
def water() -> Substance:
    return Substance.liquid('H2O', mol_weight=18.0153, density=1)


@pytest.fixture
def dmso() -> Substance:
    return Substance.liquid('DMSO', 78.13, 1.1004)


@pytest.fixture
def salt_water(water, salt) -> Container:
    return Container('sol1', max_volume=1_000, initial_contents=[(water, '100 mL'), (salt, '50 mol')])


@pytest.fixture
def empty_plate() -> Plate:
    return Plate('plate', 100)  # 100 uL


def test_make_Plate():
    with pytest.raises(ValueError, match='invalid plate name'):
        Plate(1, 10)
    with pytest.raises(ValueError, match='invalid plate name'):
        Plate('', 10)
    with pytest.raises(TypeError, match='Max volume must be a float'):
        Plate('plate', '10')
    with pytest.raises(ValueError, match='invalid plate make'):
        Plate('plate', 10, make=1)
    with pytest.raises(ValueError, match='invalid plate make'):
        Plate('plate', 10, make='')
    with pytest.raises(ValueError, match='rows must be int or list'):
        Plate('plate', 10, rows='8')
    with pytest.raises(ValueError, match='illegal number of rows'):
        Plate('plate', 10, rows=0)
    with pytest.raises(ValueError, match='columns must be int or list'):
        Plate('plate', 10, columns='8')
    with pytest.raises(ValueError, match='illegal number of columns'):
        Plate('plate', 10, columns=0)

    with pytest.raises(ValueError, match='must have at least one row'):
        Plate('plate', 10, rows=[])
    with pytest.raises(ValueError, match='row names must be strings'):
        Plate('plate', 10, rows=[1])
    with pytest.raises(ValueError, match='duplicate row names found'):
        Plate('plate', 10, rows=['a', 'a'])

    with pytest.raises(ValueError, match='must have at least one column'):
        Plate('plate', 10, columns=[])
    with pytest.raises(ValueError, match='column names must be strings'):
        Plate('plate', 10, columns=[1])
    with pytest.raises(ValueError, match='duplicate column names found'):
        Plate('plate', 10, columns=['a', 'a'])


def test_volume_and_volumes(salt, water, dmso, empty_plate):
    with pytest.raises(TypeError, match="Substance is not a valid type"):
        empty_plate.volumes('1')

    zeros = numpy.zeros(empty_plate.wells.shape)
    uL = numpy.ones(empty_plate.wells.shape)

    assert empty_plate.volume() == 0
    assert numpy.array_equal(empty_plate.volumes(), zeros)
    assert numpy.array_equal(empty_plate.volumes(water), zeros)

    new_plate = Plate.add(salt, empty_plate, '5 mol')
    assert new_plate.volume() == 0
    assert numpy.array_equal(new_plate.volumes(), zeros)
    assert numpy.array_equal(new_plate.volumes(water), zeros)
    assert numpy.array_equal(new_plate.volumes(salt), zeros)

    new_plate = Plate.add(water, new_plate, '50 uL')
    assert new_plate.volume() == (50 * uL).sum()
    assert numpy.array_equal(new_plate.volumes(), 50 * uL)
    assert numpy.array_equal(new_plate.volumes(water), 50 * uL)
    assert numpy.array_equal(new_plate.volumes(salt), zeros)

    new_plate = Plate.add(dmso, new_plate, '25 uL')
    assert new_plate.volume() == (75 * uL).sum()
    assert numpy.array_equal(new_plate.volumes(), 75 * uL)
    assert numpy.array_equal(new_plate.volumes(water), 50 * uL)
    assert numpy.array_equal(new_plate.volumes(dmso), 25 * uL)
    assert numpy.array_equal(new_plate.volumes(salt), zeros)


def test_moles(salt, water, empty_plate):
    with pytest.raises(TypeError, match="Substance is not a valid type"):
        empty_plate.moles('1')

    zeros = numpy.zeros(empty_plate.wells.shape)
    ones = numpy.ones(empty_plate.wells.shape)
    assert numpy.array_equal(empty_plate.moles(salt), zeros)

    new_plate = Plate.add(salt, empty_plate, '5 mol')
    assert numpy.array_equal(new_plate.moles(salt), 5 * ones)
    assert numpy.array_equal(new_plate.moles(water), zeros)

    new_plate = Plate.add(water, new_plate, '1 mmol')
    assert numpy.array_equal(new_plate.moles(salt), 5 * ones)
    assert numpy.array_equal(new_plate.moles(water), 0.001 * ones)

    new_plate = Plate.add(water, empty_plate, '5 uL')
    new_plate.moles(water)