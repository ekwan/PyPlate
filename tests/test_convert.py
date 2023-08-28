from pyplate.pyplate import Unit, Substance
import pytest


@pytest.fixture
def water() -> Substance:
    return Substance.liquid('H2O', mol_weight=18.0153, density=1)


@pytest.fixture
def salt() -> Substance:
    return Substance.solid('NaCl', 58.4428)


@pytest.fixture
def lipase() -> Substance:
    return Substance.enzyme('lipase')


@pytest.fixture
def dmso() -> Substance:
    return Substance.liquid('DMSO', 78.13, 1.1004)


def test_convert(salt, water, lipase, dmso):
    with pytest.raises(TypeError, match='Invalid type for substance'):
        Unit.convert(None, '', '')
    with pytest.raises(TypeError, match='Quantity must be a str'):
        Unit.convert(salt, None, '')
    with pytest.raises(TypeError, match='Unit must be a str'):
        Unit.convert(salt, '10 mL', None)

    with pytest.raises(ValueError, match='Only enzymes can be measured in activity units'):
        Unit.convert(water, '1 U', 'mL')
    with pytest.raises(ValueError, match='Enzymes can only be measured in activity units'):
        Unit.convert(lipase, '1 g', 'U')

    with pytest.raises(ValueError, match='Only liquids can be measured by volume'):
        Unit.convert(salt, '1 L', 'mol')

    # Only enzymes have activity units
    assert Unit.convert(water, '1 mL', 'U') == 0
    assert Unit.convert(lipase, '1 U', 'U') == 1

    # prefixes applied correctly
    assert Unit.convert(water, '1 mL', 'L') == 0.001
    assert Unit.convert(water, '1 L', 'mL') == 1000

    # from grams
    assert Unit.convert(water, '1 g', 'g') == 1
    assert Unit.convert(water, '1 g', 'mL') == 1 / water.density
    assert Unit.convert(water, '1 g', 'mol') == 1 / water.mol_weight

    # from moles
    assert Unit.convert(water, '1 mol', 'g') == water.mol_weight
    assert Unit.convert(water, '1 mol', 'mol') == 1
    # mol * g/mol / (g/mL)
    assert Unit.convert(water, '1 mol', 'mL') == water.mol_weight / water.density

    # from L
    assert Unit.convert(water, '1 L', 'g') == 1000 * water.density
    assert Unit.convert(water, '1 L', 'mol') == 1000 * water.density / water.mol_weight
    assert Unit.convert(water, '1 L', 'L') == 1

    # Repeat for a different liquid
    # from grams
    assert Unit.convert(dmso, '1 g', 'g') == 1
    assert Unit.convert(dmso, '1 g', 'mL') == 1 / dmso.density
    assert Unit.convert(dmso, '1 g', 'mol') == 1 / dmso.mol_weight

    # from moles
    assert Unit.convert(dmso, '1 mol', 'g') == dmso.mol_weight
    assert Unit.convert(dmso, '1 mol', 'mol') == 1
    # mol * g/mol / (g/mL)
    assert Unit.convert(dmso, '1 mol', 'mL') == dmso.mol_weight / dmso.density

    # from L
    assert Unit.convert(dmso, '1 L', 'g') == 1000 * dmso.density
    assert Unit.convert(dmso, '1 L', 'mol') == 1000 * dmso.density / dmso.mol_weight
    assert Unit.convert(dmso, '1 L', 'L') == 1

    # Repeat for a solid
    # from grams
    assert Unit.convert(salt, '1 g', 'g') == 1
    assert Unit.convert(salt, '1 g', 'mL') == 0
    assert Unit.convert(salt, '1 g', 'mol') == 1 / salt.mol_weight

    # from moles
    assert Unit.convert(salt, '1 mol', 'g') == salt.mol_weight
    assert Unit.convert(salt, '1 mol', 'mol') == 1
    assert Unit.convert(salt, '1 mol', 'mL') == 0
