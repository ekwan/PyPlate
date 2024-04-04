import pytest
import numpy
from pyplate.pyplate import Plate, Unit, config, Container


def test_make_Plate():
    """

    Test that all argument types are checked in Plate constructor.

    """
    with pytest.raises(ValueError, match='invalid plate name'):
        Plate(1, '10 uL')
    with pytest.raises(ValueError, match='invalid plate name'):
        Plate('', '10 uL')
    with pytest.raises(TypeError, match='Maximum volume must be a str'):
        Plate('plate', 10)
    with pytest.raises(ValueError, match='invalid plate make'):
        Plate('plate', '10 uL', make=1)
    with pytest.raises(ValueError, match='invalid plate make'):
        Plate('plate', '10 uL', make='')
    with pytest.raises(ValueError, match='rows must be int or list'):
        Plate('plate', '10 uL', rows='8')
    with pytest.raises(ValueError, match='illegal number of rows'):
        Plate('plate', '10 uL', rows=0)
    with pytest.raises(ValueError, match='columns must be int or list'):
        Plate('plate', '10 uL', columns='8')
    with pytest.raises(ValueError, match='illegal number of columns'):
        Plate('plate', '10 uL', columns=0)

    with pytest.raises(ValueError, match='must have at least one row'):
        Plate('plate', '10 uL', rows=[])
    with pytest.raises(ValueError, match='row names must be strings'):
        Plate('plate', '10 uL', rows=[1])
    with pytest.raises(ValueError, match='duplicate row names found'):
        Plate('plate', '10 uL', rows=['a', 'a'])

    with pytest.raises(ValueError, match='must have at least one column'):
        Plate('plate', '10 uL', columns=[])
    with pytest.raises(ValueError, match='column names must be strings'):
        Plate('plate', '10 uL', columns=[1])
    with pytest.raises(ValueError, match='duplicate column names found'):
        Plate('plate', '10 uL', columns=['a', 'a'])


def test_volume_and_volumes(salt, water, dmso, empty_plate):
    """

    Test get_volume() and get_volumes() for a plate.

    """
    epsilon = 1e-3
    with pytest.raises(TypeError, match="Substance must be a Substance"):
        empty_plate.get_volumes('1')

    zeros = numpy.zeros(empty_plate.wells.shape)
    uL = numpy.ones(empty_plate.wells.shape)
    config.precisions['uL'] = 3
    # set precision to 3 decimal places for 'uL' for testing

    salt_volume = round(Unit.convert(salt, '5 umol', 'uL'), 3)
    assert empty_plate.get_volume() == 0
    assert numpy.array_equal(empty_plate.get_volumes(), zeros)
    assert numpy.array_equal(empty_plate.get_volumes(water), zeros)

    salt_container = Container('salt', initial_contents=((salt, '1 mol'),))
    salt_container, new_plate = Plate.transfer(salt_container, empty_plate, '5 umol')
    assert new_plate.get_volume() == pytest.approx((salt_volume * uL).sum(), epsilon)
    assert numpy.allclose(new_plate.get_volumes(unit='uL'), salt_volume * uL)
    assert numpy.array_equal(new_plate.get_volumes(water), zeros)
    assert numpy.allclose(new_plate.get_volumes(salt, unit='uL'), salt_volume * uL, atol=epsilon)

    water_container = Container('water', initial_contents=((water, '1 L'),))
    water_container, new_plate = Plate.transfer(water_container, new_plate, '50 uL')
    assert new_plate.get_volume() == pytest.approx((salt_volume * uL).sum() + (50 * uL).sum(), epsilon)
    assert numpy.allclose(new_plate.get_volumes(), (salt_volume + 50) * uL)
    assert numpy.allclose(new_plate.get_volumes(water), 50 * uL)
    assert numpy.allclose(new_plate.get_volumes(salt), salt_volume * uL, atol=1e-3)

    dmso_container = Container('dmso', initial_contents=((dmso, '1 L'), ))
    dmso_container, new_plate = Plate.transfer(dmso_container, new_plate, '25 uL')
    assert new_plate.get_volume() == pytest.approx((salt_volume * uL).sum() + (75 * uL).sum(), epsilon)
    assert numpy.allclose(new_plate.get_volumes(), (salt_volume + 75) * uL)
    assert numpy.allclose(new_plate.get_volumes(water), 50 * uL)
    assert numpy.allclose(new_plate.get_volumes(dmso), 25 * uL)
    assert numpy.allclose(new_plate.get_volumes(salt), salt_volume * uL, atol=epsilon)
    assert numpy.allclose(new_plate.get_volumes(water, unit='mL'), 0.05 * uL)


def test_moles(salt, water, empty_plate):
    """

    Test moles() for a plate.

    """
    with pytest.raises(TypeError, match="Substance must be a Substance"):
        empty_plate.get_moles('1')

    zeros = numpy.zeros(empty_plate.wells.shape)
    ones = numpy.ones(empty_plate.wells.shape)
    assert numpy.array_equal(empty_plate.get_moles(salt), zeros)

    salt_container = Container('salt', initial_contents=((salt, '1 mol'),))
    salt_container, new_plate = Plate.transfer(salt_container, empty_plate, '5 umol')
    assert numpy.array_equal(new_plate.get_moles(salt, 'umol'), 5 * ones)
    assert numpy.array_equal(new_plate.get_moles(water), zeros)

    water_container = Container('water', initial_contents=((water, '1 L'),))
    water_container, new_plate = Plate.transfer(water_container, new_plate, '1 mmol')
    assert numpy.array_equal(new_plate.get_moles(salt, 'umol'), 5 * ones)
    assert numpy.array_equal(new_plate.get_moles(water, unit='mmol'), ones)

    water_container = Container('water', initial_contents=((water, '1 L'),))
    water_container, new_plate = Plate.transfer(water_container, new_plate, '5 uL')
    new_plate.get_moles(water)
