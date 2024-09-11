import pytest
from pyplate import Unit

from itertools import product

from .unit_test_constants import test_names, test_whitespace_patterns, \
                                test_prefixes, test_prefix_multipliers, \
                                test_non_parseable_quantities, \
                                test_units, test_values, \
                                test_invalid_units, test_invalid_values,  \
                                test_base_units \

def test_Unit_convert_prefix_to_multiplier():
    """
    Unit Test for `Unit.convert_prefix_to_multiplier()`

    This unit test checks for the following failure scenarios:
    - Invalid argument type (non-string) results in a `TypeError`.
    - Invalid argument value (a string that does not match a supported prefix)
      results in a `ValueError`.
    
    This unit test checks for the following success scenarios:
    - Valid argument value (a string that does match a supported prefix)
      results in returning the correct multiplier for that prefix.
    """

    # ==========================================================================
    # Failure Case: Invalid argument type
    # ==========================================================================

    for invalid_prefix in [None, 1, 2.5, False, ['str'], {}, (1,1)]:
        with pytest.raises(TypeError, match="SI prefix must be a string"):
            Unit.convert_prefix_to_multiplier(invalid_prefix)

    # ==========================================================================
    # Failure Case: Invalid string - does not match an existing prefix
    # ==========================================================================

    # Uses test_names and the test whitespace patterns to generate variations of
    # invalid prefixes
    for name in test_names:
        for pattern in test_whitespace_patterns:
            invalid_prefix = pattern.replace('e', name)
            with pytest.raises(ValueError, match="Invalid prefix"):
                Unit.convert_prefix_to_multiplier(invalid_prefix)

    # ==========================================================================
    # Success Case: Valid string - does match an existing prefix
    # ==========================================================================
    
    for prefix, multiplier in zip(test_prefixes, test_prefix_multipliers):
        result = Unit.convert_prefix_to_multiplier(prefix)
        assert result == multiplier, \
            f"Success case failed. Prefix: {prefix}  " \
            f"Expected Multiplier: {multiplier}  " \
            f"Actual Multiplier: {result}"
        

def test_Unit_convert_multiplier_to_prefix():
    """
    Unit Test for `Unit.convert_multiplier_to_prefix()`

    This unit test covers the following failure scenarios:
    - Invalid argument type (neither float nor int) results in a `TypeError`.
    - Invalid argument value (a value whose order of magnitude does not
      correspond to a multiplier of a supported prefix) results in a 
      `ValueError`.
    
    This unit tests checks for the following success scenarios:
    - Valid argument value (a value whose order of magnitude does correspond to
      a multiplier of a supported prefix) results in returning the correct 
      prefix for that multiplier.
    """

    # ==========================================================================
    # Failure Case: Invalid argument type
    # ==========================================================================

    for invalid_multiplier in [None, '', '1', [1], {}, (2.5, 3.4)]:
        with pytest.raises(TypeError, match="Multiplier must be a number"):
            Unit.convert_multiplier_to_prefix(invalid_multiplier)



    # The following base numbers will be combined with valid and invalid prefix 
    # multipliers to create a large number of permutations for testing the 
    # remaining failure case and the success case. 
    #
    # NOTE: Booleans in Python evaluate as int, so True is included here.
    base_numbers = [1, 2, 3, 8, 9, 9.99999, 8.989, 4.3, 1.80153, 7.77, True]

    # ==========================================================================
    # Failure Case: Invalid multiplier - float/int with an unsupported order of 
    #                                    magnitude  
    # ==========================================================================
    
    # Many of these have both positive and negative exponents, but some only
    # have positive exponents (e.g. 1e2 and 1e9 because 'c' and 'n' are 
    # supported prefixes but 'h' and 'G' are not)
    invalid_powers = [1e2, 1e4, 1e-4, 1e5, 1e-5, 1e7, 1e-7, 1e9, 1e10, 1e-10, 
                      1e11, 1e-11, 1e12, 1e-12, 1e13, 1e-13, 1e14, 1e-14, 
                      1e15, 1e-15]

    for sign, base, power in product([1, -1], base_numbers, invalid_powers): 
        invalid_multiplier = sign * base * power
        with pytest.raises(ValueError, match="Invalid multiplier"):
            Unit.convert_multiplier_to_prefix(invalid_multiplier)
      
    
    # NOTE: Booleans in Python evaluate as int, so False is included here as an
    # edge case. It should be treated as equivalent to 0.  
    edge_case_multipliers = [0, float('inf'), float('-inf'), float('nan'), 
                             False]

    for invalid_multiplier in edge_case_multipliers:
        with pytest.raises(ValueError, match="Invalid multiplier"):
            Unit.convert_multiplier_to_prefix(invalid_multiplier)


    # ==========================================================================
    # Success Case: Valid multiplier - float/int with a supported order of 
    #                                  magnitude  
    # ==========================================================================

    joint_mult_prefix_list = zip(test_prefix_multipliers, test_prefixes)
    test_valid_multipliers = product([-1, 1], base_numbers, 
                                     joint_mult_prefix_list)
    for sign, base, (multiplier, prefix) in test_valid_multipliers:
        valid_multiplier = sign * base * multiplier
        result = Unit.convert_multiplier_to_prefix(valid_multiplier)
        
        # This check allows for equivalent units to be recognized and treated
        # as successes (e.g. the prefixes 'u' and 'µ' are equivalent)
        assert Unit.PREFIXES[result] == Unit.PREFIXES[prefix], \
                "Expected and returned prefixes are not equivalent. " \
                f"Expected: {prefix}  Returned: {result}"    


def test_Unit_parse_quantity():
    """
    Unit Test for `Unit.parse_quantity()`

    This unit test checks for the following failure scenarios:
    - Invalid argument type (non-string) results in a `TypeError`.
    - Invalid argument value results in a `ValueError`.
      - Case: Argument cannot be parsed as a value-unit pair
        - E.g. 'asdfkm'
      - Case: Value parsed from argument is not a valid float
        - E.g 'blue mL'
      - Case: Value parsed from argument is NaN.
      - Case: Unit parsed from argument is invalid
        - E.g '0 mH'

    This unit test checks for the following success scenarios:
    - Valid argument values (the following permutations are tested)
      - All base units + various selected prefixes
      - Presence or lack of whitespace between value and units
      - Postive/Negative/Zero/Infinite values
      - Various whitespace patterns surrounding the meaningful part of the
        string
    
    These success scenarios are checked by ensuring both the parsed value and
    the parsed unit match the expected values.
    """
    
    # ==========================================================================
    # Failure Case: Argument cannot be parsed as a value-unit pair
    # ==========================================================================

    for test_quantity in test_non_parseable_quantities:
        for pattern in test_whitespace_patterns:
            merged_test_quantity = pattern.replace('e', test_quantity)
            with pytest.raises(ValueError, 
                               match=f"Could not parse '{merged_test_quantity}'"):
                Unit.parse_quantity(merged_test_quantity)

    # ==========================================================================
    # Failure Case: Value parsed from argument is not a valid float
    # ==========================================================================

    for test_quantity in test_non_parseable_quantities:
        for pattern in test_whitespace_patterns:
            merged_test_quantity = pattern.replace('e', test_quantity)
            with pytest.raises(ValueError, 
                               match=f"Could not parse '{merged_test_quantity}'"):
                Unit.parse_quantity(merged_test_quantity)

    # ==========================================================================
    # Failure Case: Value parsed from argument is not a valid float
    # ==========================================================================

    for test_value in test_invalid_values:
        for unit in test_units:
            test_quantity = test_value + ' ' + unit
            for pattern in test_whitespace_patterns:
                merged_test_quantity = pattern.replace('e', test_quantity)
                with pytest.raises(ValueError, match=f"Value \'{test_value}\' " 
                                                      "is not a valid float"):
                    Unit.parse_quantity(merged_test_quantity)

    # ==========================================================================
    # Failure Case: Value parsed from argument is 'NaN'
    # ==========================================================================

    with pytest.raises(ValueError, match=f"'NaN' values are forbidden for "
                                          "quantities"):
        Unit.parse_quantity('NaN mL')


    # ==========================================================================
    # Failure Case: Quantity 'unit' is not a valid unit
    # ==========================================================================

    for unit in test_invalid_units:
        for pattern in test_whitespace_patterns:
            merged_test_quantity = pattern.replace('e', '1 ' + unit)
            with pytest.raises(ValueError, match=f"Invalid unit"):
                Unit.parse_quantity(merged_test_quantity)

    
    # ==========================================================================
    # Success Case: Valid argument values
    # ==========================================================================

    # Set up test permutations
    joint_prefix_mult_list = zip(test_prefixes, test_prefix_multipliers)
    permutation_product = product(test_values, range(5), 
                                  joint_prefix_mult_list, test_base_units)
    
    for value_str, num_spaces, (prefix, mult), base_unit in permutation_product:
        # Vary the amount of internal whitespace for the examples
        internal_whitespace = ' ' * num_spaces

        exp_unit = prefix + base_unit
        test_qty = value_str + internal_whitespace + exp_unit
        
        # Vary the amount of external whitespace for the examples
        for pattern in test_whitespace_patterns:
            merged_test_qty = pattern.replace('e', test_qty)
            result_value, result_unit = Unit.parse_quantity(merged_test_qty)

            assert float(value_str) * mult == result_value, \
                f"Value was not parsed correctly. " \
                f"Expected: {value_str}  Result: {result_value}"
            
            assert base_unit == result_unit, \
                f"Unit was not parsed correctly. " \
                f"Expected: {base_unit}  Result: {result_unit}"
    

def test_Unit_parse_concentration():
    """
    Unit Test for `Unit.parse_concentration()`

    This unit test checks for the following failure scenarios:
    - Invalid argument type (non-string) results in a `TypeError`.
    - Invalid argument value results in a `ValueError` with the appropriate
      message.
      - Case: Argument cannot be parsed into a value-numerator-denominator
        triplet.
        - Sub-case: Argument contains unsupported concentration units.
          - E.g. ppb
        - Sub-case: Argument contains more than two groups separated by forward
                    slashes.
          - E.g. 12 mol/L/mol
      - Case: Value from parsed argument is not a valid float
        - E.g. 'red M' or '#..# mol/mL'
      - Case: Value from parsed argument is not a valid float
        - E.g. 'red M' or '#..# mol/mL'        
    """


