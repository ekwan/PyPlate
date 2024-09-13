import pytest
from pyplate import Substance, config

from copy import deepcopy
from itertools import product

from .unit_test_constants import test_names, test_whitespace_patterns, \
                                    test_positive_numbers, test_quantities, \
                                    test_units, test_values


def test_Substance___init__():
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

def test_Substance___repr__(salt, water):
    """
    Unit Test for the function `Substance.__repr__()`

    This unit test ensures that the function returns the expected string
    for both a solid and liquid example substance.
    """
    assert salt.__repr__() == "NaCl (SOLID)"
    assert water.__repr__() == "H2O (LIQUID)"

def test_Substance___eq__(salt, water, sodium_sulfate, dmso):
    """
    Unit Test for `Substance.__eq__()`

    This unit test checks the following scenarios:
    - Comparison between a Substance and a non-substance second argument
    - Comparison between a Substance and itself
    - Comparison between two identical substances
    - Comparison between two substances which are identical except for each of
      the following attributes:
      - Name
      - Type
      - Molecular weight
      - Density
      - Optional molecule parameter
    """   

    substances = [salt, water, sodium_sulfate, dmso]

    # ==========================================================================
    # False Case: Non-substance second argument
    # ==========================================================================

    for non_substance in [None, False, 1, '1', [], {}, (1,1)]:
        assert not salt == non_substance

    # ==========================================================================
    # True Case: Substance equals itself
    # ==========================================================================
    
    for substance in substances:
        assert substance == substance

    # ==========================================================================
    # True Case: Substance equals an identical substance
    # ==========================================================================

    for substance in substances:
        # For a given substance, checks both a) an identical substance created 
        # manually with the same arguments and b) a deepcopy of the substance

        identical_substance = Substance(name=substance.name, 
                                        mol_type=substance._type,
                                        mol_weight=substance.mol_weight,
                                        density=substance.density,
                                        molecule=substance.molecule
                                        )
        identical_substance_2 = deepcopy(substance)

        assert substance == identical_substance 
        assert substance == identical_substance_2

    # ==========================================================================
    # False Case: Substance does not equal another substance if any properties
    #             differ between the two
    # ==========================================================================

    for substance in substances:
        identical_substance = deepcopy(substance)
        
        # Each of these checks ensure the substances are equal before the
        # property is changed, not equal after it is changed, and equal again
        # when the property is reverted. This was added to ensure that the later
        # checks were not being "tainted" by earlier checks without having to
        # create new copies of substance for each test.

        # Different name
        assert substance == identical_substance 
        identical_substance.name = "wrong name"
        assert not substance == identical_substance 
        identical_substance.name = substance.name
        assert substance == identical_substance 

        # Different type
        assert substance == identical_substance 
        identical_substance._type = substance._type % 2 + 1 # Flips 1 <--> 2
        assert not substance == identical_substance 
        identical_substance._type = substance._type
        assert substance == identical_substance 

        # Different molecular weight
        assert substance == identical_substance 
        identical_substance.mol_weight += 0.1
        assert not substance == identical_substance 
        identical_substance.mol_weight = substance.mol_weight
        assert substance == identical_substance 

        # Different density
        assert substance == identical_substance 
        identical_substance.density += 0.1
        assert not substance == identical_substance 
        identical_substance.density = substance.density
        assert substance == identical_substance 

        # Different molecule
        assert substance == identical_substance 
        identical_substance.molecule = "wrong molecule"
        assert not substance == identical_substance 
        identical_substance.molecule = substance.molecule
        assert substance == identical_substance 

def test_Substance___hash__(salt, water, sodium_sulfate, dmso):
    """
    Unit Test for the function `Substance.__hash__()`
    
    This unit test ensures that identical substances result in the same hashing, 
    and non-identical substances hash to different results. Specifically it 
    tests the following scenarios:
    - Comparison of two calls to __hash__() by the same Substance.
    - Comparison of the hash results of two identical Substances.
    """

    substances = [salt, water, sodium_sulfate, dmso]

    # ==========================================================================
    # Equal Case: Two hashes of the same substance
    # ==========================================================================

    for substance in substances:
        assert substance.__hash__() == substance.__hash__()

    # ==========================================================================
    # Equal Case: Hashes of identical substances
    # ==========================================================================

    for substance in substances:
        # For a given substance, checks both a) an identical substance created 
        # manually with the same arguments and b) a deepcopy of the substance

        identical_substance = Substance(name=substance.name, 
                                        mol_type=substance._type,
                                        mol_weight=substance.mol_weight,
                                        density=substance.density,
                                        molecule=substance.molecule
                                        )
        identical_substance_2 = deepcopy(substance)

        assert substance.__hash__() == identical_substance.__hash__()
        assert substance.__hash__() == identical_substance_2.__hash__()

@pytest.mark.filterwarnings("ignore:Density not provided")
def test_Substance_solid():
    """
    Unit Test for the function `Substance.solid()`

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

    # ==========================================================================
    # Success Case: Density not provided
    # ==========================================================================

    # NOTE: This is a non-recommended case, but one that is still being allowed
    # at the moment. 

    solid = Substance.solid('salt', 58.44)
    assert solid.name == 'salt'
    assert solid._type == Substance.SOLID
    assert solid.mol_weight == 58.44
    assert solid.density == config.default_solid_density
    
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

def test_Substance_convert(salt, water, sodium_sulfate, dmso):
    """
    Unit Test for `Substance.convert()`
    
    This unit test checks the following failure scenarios:
    - Invalid argument types result in a `TypeError`
    - Invalid argument values result in a `ValueError`
    
    This unit test checks the following success scenarios:
    - Large premutations of prefixed units for all base types
      - NOTE: These examples are only checked to ensure no errors are thrown, 
        as automatically computing the expected result for each permutation 
        would require an implementation akin to the function being tested.
    - Specific successful conversions for the permutations of each base unit.
      - NOTE: These examples are checked to ensure the values themselves are
        correct. They contain both prefixed and unprefixed base units, and cover
        all nine combinations of the three base units: 'g', 'mol', and 'L'.

    """
    
    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================

    for invalid_val_argument in [None, '', '1', (1,1), [], [25, 35], {}, {1:1}]:
        with pytest.raises(TypeError, match='Quantity must be a float'):
            salt.convert(invalid_val_argument, 'mL', 'mL')

    for invalid_unit_argument in [None, False, 1, (1,1), ['10 mL'], {}]:
        with pytest.raises(TypeError, match='\'From unit\' must be a str'):
            salt.convert(1, invalid_unit_argument, 'mL')
        with pytest.raises(TypeError, match='\'To unit\' must be a str'):
            salt.convert(1, 'mL', invalid_unit_argument)


    # ==========================================================================
    # Failure Case: Invalid argument values
    # ==========================================================================

    # NOTE: Error messages are not checked here to avoid coupling this unit test
    # to the implementations of other functions. 

    # Test invalid 'from unit' str
    with pytest.raises(ValueError):
        salt.convert(1, 'mA', 'mL')

    # Test invalid 'to unit' str
    with pytest.raises(ValueError):
        salt.convert(10, 'mL', '1')


    # ==========================================================================
    # Success Cases: Large permutations of prefixed units 
    # ==========================================================================
    
    # Does not check result, only ensures that these calls do not throw errors
    for value, from_unit, to_unit in product(test_values, test_units, test_units):
        salt.convert(float(value), from_unit, to_unit)
        water.convert(float(value), from_unit, to_unit)
        dmso.convert(float(value), from_unit, to_unit)


    # ==========================================================================
    # Success Cases: Specific successful conversions 
    # ==========================================================================

    # Check that prefixes are applied correctly
    assert water.convert(1, 'mL', 'L') == 0.001
    assert water.convert(1, 'L', 'mL') == 1000
    assert water.convert(1, 'ug', 'mg') == 0.001
    assert water.convert(1, 'g', 'ug') == 1000000

    tol = 1e-24

    for substance in [salt, water, sodium_sulfate, dmso]:
        # Check conversions from grams
        assert substance.convert(1, 'g', 'g') == 1

        assert substance.convert(1, 'g', 'mol') == 1 / substance.mol_weight
        assert substance.convert(1, 'g', 'mmol') == pytest.approx(1000 / substance.mol_weight, rel=tol)
        assert substance.convert(1, 'kg', 'mol') == pytest.approx(1000 / substance.mol_weight, rel=tol)

        assert substance.convert(1, 'g', 'L') == pytest.approx(0.001 / substance.density, rel=tol)
        assert substance.convert(1, 'g', 'mL') == pytest.approx(1 / substance.density, rel=tol)
        assert substance.convert(1, 'kg', 'L') == pytest.approx(1 / substance.density, rel=tol)
        
        # Check conversions from moles
        assert substance.convert(1, 'mol', 'mol') == 1

        assert substance.convert(1, 'mol', 'g') == substance.mol_weight
        assert substance.convert(1, 'mol', 'mg') == 1000 * substance.mol_weight
        assert substance.convert(1, 'mmol', 'g') == 0.001 * substance.mol_weight
        
        assert substance.convert(1, 'mol', 'mL') == pytest.approx(substance.mol_weight / substance.density, rel=tol)
        assert substance.convert(1, 'mol', 'L') == pytest.approx(0.001 * substance.mol_weight / substance.density, rel=tol)

        # Check conversions from L
        assert substance.convert(1, 'L', 'L') == 1
        
        assert substance.convert(1, 'L', 'g') == 1000 * substance.density
        assert substance.convert(1, 'L', 'kg') == substance.density
        assert substance.convert(1, 'mL', 'g') == substance.density

        assert substance.convert(1, 'L', 'mol') == pytest.approx(1000 * substance.density / substance.mol_weight, rel=tol)
        assert substance.convert(1, 'L', 'mol') == pytest.approx(1000 * substance.density / substance.mol_weight, rel=tol)
        assert substance.convert(1, 'L', 'mol') == pytest.approx(1000 * substance.density / substance.mol_weight, rel=tol)

def test_Substance_convert_quantity(salt, water, sodium_sulfate, dmso):
    """
    Unit Test for `Substance.convert_quantity()`
    
    This unit test checks the following failure scenarios:
    - Invalid argument types result in a `TypeError`
    - Invalid argument values result in a `ValueError`
      - NOTE: All instances of invalid values are handled in the calls to other
        functions, so only one failure example for each parameter is included
        here, and the error message is not checked.
    
    This unit test checks the following success scenarios:
    - Large premutations of prefixed units for all base types
      - NOTE: These examples are only checked to ensure no errors are thrown, 
        as automatically computing the expected result for each permutation 
        would require an implementation akin to the function being tested.

    - Specific successful conversions for the permutations of each base unit.
      - NOTE: These examples are checked to ensure the values themselves are
        correct. They contain both prefixed and unprefixed base units, and cover
        all nine combinations of the three base units: 'g', 'mol', and 'L'.

    """
    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================

    for invalid_argument in [None, False, 1, (1,1), ['10 mL'], {}]:
        with pytest.raises(TypeError, match='Quantity must be a str'):
            salt.convert_quantity(invalid_argument, '')
        with pytest.raises(TypeError, match='Unit must be a str'):
            salt.convert_quantity('10 mL', invalid_argument)


    # ==========================================================================
    # Failure Case: Invalid argument values
    # ==========================================================================

    # NOTE: Error messages are not checked here to avoid coupling this unit test
    # to the implementations of other functions. 

    # Test invalid quantity str
    with pytest.raises(ValueError):
        salt.convert_quantity('mL', 'mL')
    with pytest.raises(ValueError):
        salt.convert_quantity('inf', 'mL')
    with pytest.raises(ValueError):
        salt.convert_quantity('-### L', 'mL')
    with pytest.raises(ValueError):
        salt.convert_quantity('10 K', 'mL')

    # Test invalid unit str
    with pytest.raises(ValueError):
        salt.convert_quantity('10 mL', '1')
    with pytest.raises(ValueError):
        salt.convert_quantity('10 mL', 'F')


    # ==========================================================================
    # Success Cases: Large permutations of prefixed units 
    # ==========================================================================
    
    # Does not check result, only ensures that these calls do not throw errors
    for test_quantity, test_unit in product(test_quantities, test_units):
        salt.convert_quantity(test_quantity, test_unit)
        water.convert_quantity(test_quantity, test_unit)
        dmso.convert_quantity(test_quantity, test_unit)


    # ==========================================================================
    # Success Cases: Specific successful conversions 
    # ==========================================================================

    # Check that prefixes are applied correctly
    assert water.convert_quantity('1 mL', 'L') == 0.001
    assert water.convert_quantity('1 L', 'mL') == 1000
    assert water.convert_quantity('1 ug', 'mg') == 0.001
    assert water.convert_quantity('1 g', 'ug') == 1000000

    tol = 1e-24

    for substance in [salt, water, sodium_sulfate, dmso]:
        # Check conversions from grams
        assert substance.convert_quantity('1 g', 'g') == 1

        assert substance.convert_quantity('1 g', 'mol') == 1 / substance.mol_weight
        assert substance.convert_quantity('1 g', 'mmol') == pytest.approx(1000 / substance.mol_weight, rel=tol)
        assert substance.convert_quantity('1 kg', 'mol') == pytest.approx(1000 / substance.mol_weight, rel=tol)

        assert substance.convert_quantity('1 g', 'L') == pytest.approx(0.001 / substance.density, rel=tol)
        assert substance.convert_quantity('1 g', 'mL') == pytest.approx(1 / substance.density, rel=tol)
        assert substance.convert_quantity('1 kg', 'L') == pytest.approx(1 / substance.density, rel=tol)
        
        # Check conversions from moles
        assert substance.convert_quantity('1 mol', 'mol') == 1

        assert substance.convert_quantity('1 mol', 'g') == substance.mol_weight
        assert substance.convert_quantity('1 mol', 'mg') == 1000 * substance.mol_weight
        assert substance.convert_quantity('1 mmol', 'g') == 0.001 * substance.mol_weight
        
        assert substance.convert_quantity('1 mol', 'mL') == pytest.approx(substance.mol_weight / substance.density, rel=tol)
        assert substance.convert_quantity('1 mol', 'L') == pytest.approx(0.001 * substance.mol_weight / substance.density, rel=tol)

        # Check conversions from L
        assert substance.convert_quantity('1 L', 'L') == 1
        
        assert substance.convert_quantity('1 L', 'g') == 1000 * substance.density
        assert substance.convert_quantity('1 L', 'kg') == substance.density
        assert substance.convert_quantity('1 mL', 'g') == substance.density

        assert substance.convert_quantity('1 L', 'mol') == pytest.approx(1000 * substance.density / substance.mol_weight, rel=tol)
        assert substance.convert_quantity('1 L', 'mol') == pytest.approx(1000 * substance.density / substance.mol_weight, rel=tol)
        assert substance.convert_quantity('1 L', 'mol') == pytest.approx(1000 * substance.density / substance.mol_weight, rel=tol)
