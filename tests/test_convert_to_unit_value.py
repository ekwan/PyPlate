from PyPlate import Substance
import pytest

EPSILON = 1e-6


def test_convert_to_unit_value_solid_g():
    solid = Substance.solid('NaCl', 58.4428)
    moles = solid.convert_to_unit_value('10 mg')
    assert abs(moles - 0.01 / 58.4428) < EPSILON

    moles = solid.convert_to_unit_value('10 g')
    assert abs(moles - 10 / 58.4428) < EPSILON


def test_convert_to_unit_value_solid_L():
    solid = Substance.solid('NaCl', 58.4428)
    with pytest.raises(ValueError):
        solid.convert_to_unit_value('1 L')

    with pytest.raises(ValueError):
        solid.convert_to_unit_value('1 mL')


def test_convert_to_unit_value_solid_mol():
    solid = Substance.solid('NaCl', 58.4428)
    moles = solid.convert_to_unit_value('1 mol')
    assert moles == 1



def test_convert_to_unit_value_solid_AU():
    solid = Substance.solid('NaCl', 58.4428)
    with pytest.raises(ValueError):
        solid.convert_to_unit_value('1 AU')


def test_convert_to_unit_value_solid_garbage():
    solid = Substance.solid('NaCl', 58.4428)
    with pytest.raises(ValueError):
        solid.convert_to_unit_value('1 garbage')


###########################
def test_convert_to_unit_value_liquid_g():
    liquid = Substance.liquid('H2O', 18.0153, 1)
    volume = liquid.convert_to_unit_value('1 g')
    assert volume == 1

    volume = liquid.convert_to_unit_value('1 mg')
    assert volume == 1e-3

    liquid = Substance.liquid('H2O', 18.0153, 10)
    volume = liquid.convert_to_unit_value('1 g')
    assert volume == 0.1


def test_convert_to_unit_value_liquid_L():
    liquid = Substance.liquid('H2O', 18.0153, 1)
    volume = liquid.convert_to_unit_value('1 L')
    assert volume == 1000

    volume = liquid.convert_to_unit_value('1 mL')
    assert volume == 1


def test_convert_to_unit_value_liquid_mol():
    liquid = Substance.liquid('H2O', 18.0153, 1)
    volume = liquid.convert_to_unit_value('1 Mmol')
    assert abs(volume - 18.0153) < EPSILON



def test_convert_to_unit_value_liquid_AU():
    liquid = Substance.liquid('H2O', 18.0153, 1)
    with pytest.raises(ValueError):
        liquid.convert_to_unit_value('1 AU')


def test_convert_to_unit_value_liquid_garbage():
    liquid = Substance.liquid('H2O', 18.0153, 1)
    with pytest.raises(ValueError):
        liquid.convert_to_unit_value('1 garbage')


def test_convert_to_unit_value_enzyme():
    enzyme = Substance.enzyme('Lactase')
    for amount in ['1 mg', '1 mL', '1 mol', '1 garbage']:
        with pytest.raises(ValueError):
            enzyme.convert_to_unit_value(amount)

    assert enzyme.convert_to_unit_value('1 AU') == 1
    assert enzyme.convert_to_unit_value('10 AU') == 10
