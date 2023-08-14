from pyplate.pyplate import Substance, Unit
import pytest

EPSILON = 1e-6


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


def test_convert_to_unit_value_solid_g(salt):
    moles = Unit.convert_to_unit_value(salt, '10 mg')
    assert abs(moles - Unit.convert_to_storage(0.01 / 58.4428, 'mol')) < EPSILON

    moles = Unit.convert_to_unit_value(salt, '10 g')
    assert abs(moles - Unit.convert_to_storage(10 / 58.4428, 'mol')) < EPSILON


def test_convert_to_unit_value_solid_L(salt):
    with pytest.raises(ValueError):
        Unit.convert_to_unit_value(salt, '1 L')

    with pytest.raises(ValueError):
        Unit.convert_to_unit_value(salt, '1 mL')


def test_convert_to_unit_value_solid_mol(salt):
    moles = Unit.convert_to_unit_value(salt, '1 mol')
    assert moles == Unit.convert_to_storage(1, 'mol')


def test_convert_to_unit_value_solid_U(salt):
    with pytest.raises(ValueError):
        Unit.convert_to_unit_value(salt, '1 U')


def test_convert_to_unit_value_solid_garbage(salt):
    with pytest.raises(ValueError):
        Unit.convert_to_unit_value(salt, '1 garbage')


###########################
def test_convert_to_unit_value_liquid_g(water, dmso):
    volume = Unit.convert_to_unit_value(water, '1 g')
    assert volume == Unit.convert_to_storage(1, 'mL')

    volume = Unit.convert_to_unit_value(water, '1 mg')
    assert volume == Unit.convert_to_storage(1e-3, 'mL')

    volume = Unit.convert_to_unit_value(dmso, '1 g')
    assert volume == Unit.convert_to_storage(1/1.1004, 'mL')


def test_convert_to_unit_value_liquid_L(water):
    volume = Unit.convert_to_unit_value(water, '1 L')
    assert volume == Unit.convert_to_storage(1000, 'mL')

    volume = Unit.convert_to_unit_value(water, '1 mL')
    assert volume == Unit.convert_to_storage(1, 'mL')


def test_convert_to_unit_value_liquid_mol(water, dmso):
    volume = Unit.convert_to_unit_value(water, '1 mol')
    assert abs(volume - Unit.convert_to_storage(18.0153, 'mL')) < EPSILON
    volume = Unit.convert_to_unit_value(dmso, '1 mol')
    assert abs(volume - Unit.convert_to_storage(78.13/1.1004, 'mL')) < EPSILON


def test_convert_to_unit_value_liquid_U(water):
    with pytest.raises(ValueError):
        Unit.convert_to_unit_value(water, '1 U')


def test_convert_to_unit_value_liquid_garbage(water):
    with pytest.raises(ValueError):
        Unit.convert_to_unit_value(water, '1 garbage')


def test_convert_to_unit_value_enzyme():
    lactase = Substance.enzyme('Lactase')
    for amount in ['1 mg', '1 mL', '1 mol', '1 garbage']:
        with pytest.raises(ValueError):
            Unit.convert_to_unit_value(lactase, amount)

    assert Unit.convert_to_unit_value(lactase, '1 U') == 1
    assert Unit.convert_to_unit_value(lactase, '10 U') == 10
