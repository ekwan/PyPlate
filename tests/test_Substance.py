import pytest
from pyplate import Substance

from itertools import product

from .unit_test_constants import test_names, test_whitespace_patterns, \
                                    test_positive_numbers


def test_Substance__init__():
    """
    Unit Test for the function `Substance.__init__()`.

    This unit test checks the following failure scenarios:
    - Arguments with invalid types throw a `TypeError`
    - Arguments with invalid values throw a `ValueError`. These include:
        - The empty string for `name`
        - Invalid type of substance (i.e. not a solid or liquid)
        - Negative, zero, or NaN values for molecular weight / density

    This unit test also checks the following success scenarios:
    - Various string options for names
    - Various positive values for substance molecular weight and density
      properties. 
        - NOTE: At present, this includes the edge case of positive 
          infinity.
    - Various arbitrary values for the optional molecule parameter.
        - NOTE: At present, this parameter is entirely unused, so passing it
          any value is currently considered acceptable behavior.

    In each of the scenarios above, the test checks that each of the arguments 
    passed to `Substance()` are correctly set as the attributes of the returned
    Substance object.
    """
    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================

    with pytest.raises(TypeError, match="Name must be a str"):
        Substance(1, Substance.SOLID, 1, 1)
    with pytest.raises(TypeError, match="Name must be a str"):
        Substance([], Substance.SOLID, 1, 1)
    with pytest.raises(TypeError, match="Name must be a str"):
        Substance({}, Substance.SOLID, 1, 1)

    with pytest.raises(TypeError, match="Type must be an int\\."):
        Substance('unknown', [], 1, 1)
    with pytest.raises(TypeError, match="Type must be an int\\."):
        Substance('unknown', "1", 1, 1)
    with pytest.raises(TypeError, match="Type must be an int\\."):
        Substance('unknown', {}, 1, 1)

    with pytest.raises(TypeError, match="Molecular weight must be a float"):
        Substance('salt', Substance.SOLID, [], 1)
    with pytest.raises(TypeError, match="Molecular weight must be a float"):
        Substance('salt', Substance.SOLID, '1', 1)

    with pytest.raises(TypeError, match="Density must be a float"):
        Substance('water', Substance.LIQUID, 18.0153, [])
    with pytest.raises(TypeError, match="Density must be a float"):
        Substance('water', Substance.LIQUID, 18.0153, "1")

    # ==========================================================================
    # Failure Case: Empty name
    # ==========================================================================

    with pytest.raises(ValueError, match="Name must not be empty"):
        Substance('', Substance.SOLID, 1, 1)

    # ==========================================================================
    # Failure Case: Unsupported type of Substance
    # ==========================================================================

    with pytest.raises(ValueError, match="Substance type unsupported\\."):
        Substance('gas', 3, 1, 1)
    with pytest.raises(ValueError, match="Substance type unsupported\\."):
        Substance('unknown', 0, 1, 1)
    with pytest.raises(ValueError, match="Substance type unsupported\\."):
        Substance('dark_matter', -1, 1, 1)

    # ==========================================================================
    # Failure Case: Negative, zero, and NaN values for molecular weight 
    #               & density
    # ==========================================================================

    with pytest.raises(ValueError, match="Molecular weight must be positive"):
        Substance('salt', Substance.SOLID, -1, 1)
    with pytest.raises(ValueError, match="Molecular weight must be positive"):
        Substance('water', Substance.LIQUID, 0, 1)
    with pytest.raises(ValueError, match="Molecular weight must be positive"):
        Substance('salt', Substance.SOLID, -float('inf'), 1)
    with pytest.raises(ValueError, match="Molecular weight must be positive"):
        Substance('salt', Substance.LIQUID, float('nan'), 1)

    with pytest.raises(ValueError, match="Density must be positive"):
        Substance('salt', Substance.SOLID, 1, -1)
    with pytest.raises(ValueError, match="Density must be positive"):
        Substance('salt', Substance.LIQUID, 1, 0)
    with pytest.raises(ValueError, match="Density must be positive"):
        Substance('salt', Substance.SOLID, 1, -float('inf'))
    with pytest.raises(ValueError, match="Density must be positive"):
        Substance('salt', Substance.LIQUID, 1, float('nan'))

    # ==========================================================================
    # Success Case: Variations in names
    # ==========================================================================    

    for test_name in test_names:
        for inner_idx, pattern in enumerate(test_whitespace_patterns):
            test_name = pattern.replace('e', test_name)
            # Test variations of substance types using the inner index
            mol_type = Substance.SOLID if inner_idx % 2 else Substance.LIQUID
            substance = Substance(test_name, mol_type, 1, 1)

            assert substance.name == test_name
            assert substance._type == mol_type
            assert substance.mol_weight == 1
            assert substance.density == 1

    # At present, pure whitespace substance names are allowed. Switch this to a
    # failure case in the constructor if such names are ever disallowed.
    for idx, pattern in enumerate(test_whitespace_patterns):
        test_name = pattern.replace('e', ' ')
        # Test variations of substance types using the inner index
        mol_type = Substance.SOLID if idx % 2 else Substance.LIQUID
        substance = Substance(test_name, mol_type, 18.0153, 2.17)
        
        assert substance.name == test_name
        assert substance._type == mol_type
        assert substance.mol_weight == 18.0153
        assert substance.density == 2.17

    # ==========================================================================
    # Success Case: Variations in positive values for molecular weight & 
    #               density
    # ==========================================================================

    for idx, (mol_weight, density) in enumerate(product(test_positive_numbers + 
                                                        [float('inf')], repeat=2)):
        # Test variations of substance types using the inner index
        mol_type = Substance.SOLID if idx % 2 else Substance.LIQUID
        substance = Substance('test_substance', mol_type, mol_weight, density)

        assert substance.name == 'test_substance'
        assert substance._type == mol_type
        assert substance.mol_weight == mol_weight
        assert substance.density == density

    # ==========================================================================
    # Success Case: Variations in arbitrary values for optional molecule 
    #               parameter
    # ==========================================================================
    
    for idx, molecule in enumerate([None, '', 'abcd', 1, [], (6,5), {}]):
        # Test variations of substance types using the inner index
        mol_type = Substance.SOLID if idx % 2 else Substance.LIQUID
        substance = Substance('test_substance', mol_type, 18.0153, 1, molecule)
        
        assert substance.name == 'test_substance'
        assert substance.mol_weight == 18.0153
        assert substance.density == 1
        assert substance.molecule == molecule

def test_Substance_solid():
    """
    Unit Test for the function `Substance.solid()`.

    This unit test does not have any failure scenarios, as these are triggered
    by the call to the constructor. 
   
    This unit test checks the following success scenarios:
    - Various string options for names
    - Various positive values for substance molecular weight and density
      properties. 
        - NOTE: At present, this includes the edge case of positive 
          infinity.
    - Various arbitrary values for the optional molecule parameter.
        - NOTE: At present, this parameter is entirely unused, so passing it
          any value is currently considered acceptable behavior.

    In each of the scenarios above, the test checks that each of the arguments 
    passed to `Substance.solid()` are correctly set as the attributes of the 
    returned `Substance` and that the `_type` attribute of the `Substance` is
    `Substance.SOLID`.
    """
    # ==========================================================================
    # Success Case: Variations in names
    # ==========================================================================    

    for test_name in test_names:
        for pattern in test_whitespace_patterns:
            test_name = pattern.replace('e', test_name)
            solid = Substance.solid(test_name, 58.44, 2.17)

            assert solid.name == test_name
            assert solid._type == Substance.SOLID
            assert solid.mol_weight == 58.44
            assert solid.density == 2.17

    # At present, pure whitespace substance names are allowed. Switch this to a
    # failure case in the constructor if such names are ever disallowed.
    for pattern in test_whitespace_patterns:
        test_name = pattern.replace('e', ' ')
        solid = Substance.solid(test_name, 58.44, 2.17)
        assert solid.name == test_name
        assert solid._type == Substance.SOLID
        assert solid.mol_weight == 58.44
        assert solid.density == 2.17

    # ==========================================================================
    # Success Case: Variations in positive values for molecular weight & 
    #               density
    # ==========================================================================

    for mol_weight, density in product(test_positive_numbers + [float('inf')], 
                                       repeat=2):
        solid = Substance.solid('test_solid', mol_weight, density)
        assert solid.name == 'test_solid'
        assert solid._type == Substance.SOLID
        assert solid.mol_weight == mol_weight
        assert solid.density == density

    # ==========================================================================
    # Success Case: Variations in arbitrary values for optional molecule 
    #               parameter
    # ==========================================================================
    
    for molecule in [None, '', 'abcd', 1, [], (6,5), {}]:
        solid = Substance.solid('test_solid', 58.44, 2.17, molecule)
        assert solid.name == 'test_solid'
        assert solid._type == Substance.SOLID
        assert solid.mol_weight == 58.44
        assert solid.density == 2.17
        assert solid.molecule == molecule



def test_Substance_liquid():
    """
    Unit Test for the function `Substance.liquid()`.

    This unit test does not have any failure scenarios, as these are triggered
    by the call to the constructor. 
   
    This unit test checks the following success scenarios:
    - Various string options for names
    - Various positive values for substance molecular weight and density
      properties. 
        - NOTE: At present, this includes the edge case of positive 
          infinity.
    - Various arbitrary values for the optional molecule parameter.
        - NOTE: At present, this parameter is entirely unused, so passing it
          any value is currently considered acceptable behavior.

    In each of the scenarios above, the test checks that each of the arguments 
    passed to `Substance.liquid()` are correctly set as the attributes of the 
    returned `Substance` and that the `_type` attribute of the `Substance` 
    object is `Substance.LIQUID`.
    """
    # ==========================================================================
    # Success Case: Variations in names
    # ==========================================================================    

    for test_name in test_names:
        for pattern in test_whitespace_patterns:
            test_name = pattern.replace('e', test_name)
            liquid = Substance.liquid(test_name, 18.0153, 1)

            assert liquid.name == test_name
            assert liquid._type == Substance.LIQUID
            assert liquid.mol_weight == 18.0153
            assert liquid.density == 1

    # At present, pure whitespace substance names are allowed. Switch this to a
    # failure case in the constructor if such names are ever disallowed.
    for pattern in test_whitespace_patterns:
        test_name = pattern.replace('e', ' ')
        liquid = Substance.liquid(test_name, 18.0153, 1)
        assert liquid.name == test_name
        assert liquid._type == Substance.LIQUID
        assert liquid.mol_weight == 18.0153
        assert liquid.density == 1

    # ==========================================================================
    # Success Case: Variations in positive values for molecular weight & 
    #               density
    # ==========================================================================

    for mol_weight, density in product(test_positive_numbers + [float('inf')], 
                                       repeat=2):
        liquid = Substance.liquid('test_liquid', mol_weight, density)
        assert liquid.name == 'test_liquid'
        assert liquid._type == Substance.LIQUID
        assert liquid.mol_weight == mol_weight
        assert liquid.density == density

    # ==========================================================================
    # Success Case: Variations in arbitrary values for optional molecule 
    #               parameter
    # ==========================================================================
    
    for molecule in [None, '', 'abcd', 1, [], (6,5), {}]:
        liquid = Substance.liquid('test_liquid', 18.0153, 1, molecule)
        assert liquid.name == 'test_liquid'
        assert liquid._type == Substance.LIQUID
        assert liquid.mol_weight == 18.0153
        assert liquid.density == 1
        assert liquid.molecule == molecule


def test_Substance_is_solid(salt, water, sodium_sulfate, dmso):
    """
    Unit Test for the method `Substance.is_solid()`.

    This unit test checks the following scenarios:
    - Solid substances return `True`
    - Non-solid substances (for now, this means liquids) return `False`
    """
    assert salt.is_solid() is True
    assert water.is_solid() is False
    assert sodium_sulfate.is_solid() is True
    assert dmso.is_solid() is False


def test_Substance_is_liquid(salt, water, sodium_sulfate, dmso):
    """
    Unit Test for the method `Substance.is_liquid()`.

    This unit test checks the following scenarios:
    - Liquid substances return `True`
    - Non-liquid substances (for now, this means solids) return `False`
    """
    assert salt.is_liquid() is False
    assert water.is_liquid() is True
    assert sodium_sulfate.is_liquid() is False
    assert dmso.is_liquid() is True


