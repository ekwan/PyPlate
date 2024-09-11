import pytest
from pyplate import Substance


def test_convert(salt, water, dmso):
    """

    Test internal conversion utilities.

    """
    # Argument types checked
    with pytest.raises(TypeError, match='Quantity must be a str'):
        salt.convert(None, '')
    with pytest.raises(TypeError, match='Unit must be a str'):
        salt.convert('10 mL', None)

    # prefixes applied correctly
    assert water.convert('1 mL', 'L') == 0.001
    assert water.convert('1 L', 'mL') == 1000

    # from grams
    assert water.convert('1 g', 'g') == 1
    assert water.convert('1 g', 'mL') == 1 / water.density
    assert water.convert('1 g', 'mol') == 1 / water.mol_weight

    # from moles
    assert water.convert('1 mol', 'g') == water.mol_weight
    assert water.convert('1 mol', 'mol') == 1
    # mol * g/mol / (g/mL)
    assert water.convert('1 mol', 'mL') == water.mol_weight / water.density

    # from L
    assert water.convert('1 L', 'g') == 1000 * water.density
    assert water.convert('1 L', 'mol') == 1000 * water.density / water.mol_weight
    assert water.convert('1 L', 'L') == 1

    # Repeat for a different liquid
    # from grams
    assert dmso.convert('1 g', 'g') == 1
    assert dmso.convert('1 g', 'mL') == 1 / dmso.density
    assert dmso.convert('1 g', 'mol') == 1 / dmso.mol_weight

    # from moles
    assert dmso.convert('1 mol', 'g') == dmso.mol_weight
    assert dmso.convert('1 mol', 'mol') == 1
    # mol * g/mol / (g/mL)
    assert dmso.convert('1 mol', 'mL') == dmso.mol_weight / dmso.density

    # from L
    assert dmso.convert('1 L', 'g') == 1000 * dmso.density
    assert dmso.convert('1 L', 'mol') == 1000 * dmso.density / dmso.mol_weight
    assert dmso.convert('1 L', 'L') == 1

    # Repeat for a solid
    # from grams
    assert salt.convert('1 g', 'g') == 1
    assert salt.convert('1 g', 'mL') == 1 / salt.density
    assert salt.convert('1 g', 'mol') == 1 / salt.mol_weight

    # from moles
    assert salt.convert('1 mol', 'g') == salt.mol_weight
    assert salt.convert('1 mol', 'mol') == 1
    assert salt.convert('1 mol', 'mL') == pytest.approx(salt.mol_weight / salt.density)
