import pytest
from pyplate import Substance, Unit, config

import math

from itertools import product

from .unit_test_constants import test_names, test_whitespace_patterns, \
                                test_prefixes, test_prefix_multipliers, \
                                test_non_parseable_quantities, \
                                test_units, test_units_bases_and_mults, \
                                test_invalid_units, test_invalid_values,  \
                                test_base_units, test_values \

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

def test_Unit_parse_prefixed_unit():
    """
    Unit Test for `Unit.parse_prefixed_unit()`

    This unit test checks for the following failure scenarios:
    - Invalid argument type (non-string) results in a `TypeError`
    - Invalid argument value results in a `ValueError`
      - Case: Argument does not end with a base unit or 'M'
      - Case: Argument does not have a valid prefix

    This unit test checks for the following success scenarios:
    - Valid unprefixed base unit
    - Valid prefixed unit

    These success scenarios are checked to ensure correctness of both the 
    returned multiplier and the base unit.
    """

    # ==========================================================================
    # Failure Case: Invalid argument type
    # ==========================================================================

    for non_str in [None, False, 1, ('1',), ['1'], {}]:
        with pytest.raises(TypeError, match="Unit must be a str\\."):
            Unit.parse_prefixed_unit(non_str)


    # ==========================================================================
    # Failure Case: Invalid argument value - invalid base unit
    # ==========================================================================
    
    for unit in test_invalid_units:
        with pytest.raises(ValueError, match="Invalid unit"):
            Unit.parse_prefixed_unit(unit)


    # ==========================================================================
    # Failure Case: Invalid argument value - invalid prefix
    # ==========================================================================
    
    for unit in ['jmol', 'ig', 'yL', 'Tmol', 'mmmmol', 'gg', 'L mL']:
        with pytest.raises(ValueError, match="Invalid prefix"):
            Unit.parse_prefixed_unit(unit)

    
    # ==========================================================================
    # Success Cases
    # ==========================================================================

    for unit in test_units:
        expected_base_unit, expected_mult = test_units_bases_and_mults[unit]
        result_base_unit, result_mult = Unit.parse_prefixed_unit(unit)

        assert expected_base_unit == result_base_unit
        assert expected_mult == result_mult

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
    # Failure Case: Invalid argument type
    # ==========================================================================

    for invalid_qty in [None, False, 1, ('1',), ['1'], {}]:
        with pytest.raises(TypeError, match="Quantity must be a str"):
            Unit.parse_quantity(invalid_qty)

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
    # Failure Case: Unit parsed from argument is not a valid unit
    # ==========================================================================

    for unit in test_invalid_units:
        for pattern in test_whitespace_patterns:
            merged_test_quantity = pattern.replace('e', '1 ' + unit)
            with pytest.raises(ValueError):
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
      - Case: Argument contains no slashes and the provided unit is not a
              supported concentration unit ('m' or 'M').
      - Case: Argument contains more than two groups separated by forward
              slashes.
      - Case: Numerator from parsed argument is invalid.
        - Sub-Case: Numerator cannot be parsed into a value & unit.
        - Sub-Case: Numerator value is not a valid float.
          - E.g. 'red M' or '#..# mol/mL'
        - Sub-Case: Numerator value is NaN.
        - Sub-Case: Numerator unit is not a valid unit. 
          - E.g. '10 red/L', '12 ggg/mL', '5 M/L'       
      - Case: Denominator from parsed argument is invalid.
        - Sub-Case: Denominator cannot be parsed into either a unit or a 
                      value & unit.
        - Sub-Case: Denominator value is not a valid float.
          - E.g. '10 g/2.4.4 mols' or '12 mmol/-- L' 
        - Sub-Case: Denominator value is NaN.
        - Sub-Case: Denominator unit is not a valid unit.
          - E.g. '10 mol/K', '2 g / 12 Lalas', '7 mL/M', '2 mol/m'
        - Sub-Case: Denominator value is zero.
      - Case: The resulting concentration value is NaN.
        - E.g. 'inf mol/inf L'

    
    This unit test checks for the following success scenarios:
    - Concentrations formatted as 'value concentration unit'
    - Concentrations formatted as 'value weight/volume %'
    - Concentrations formatted as 'value unit/unit'
    - Concentrations formatted as 'value unit/value unit'
    - Specific, manually created examples (these will cover all of the above
      categories, in case the permutation-based tests of the categories are
      flawed)

    Each of the above success scenarios is tested to ensure that the value, 
    numerator unit, and denominator unit of the parsed result are all 
    as expected.
    """
    
    # ==========================================================================
    # Failure Case: Invalid argument type (non-string)
    # ==========================================================================

    for invalid_unit in [None, False, 1, (1,1), [], {}, 9.81]:
        with pytest.raises(TypeError, match="Concentration must be str\\."):
            Unit.parse_concentration(invalid_unit)


    # ==========================================================================
    # Failure Case: Invalid argument value - invalid concentration unit
    # ==========================================================================

    for invalid_unit in ['A', 'S', 'mF', 'laskdf', '']:
        with pytest.raises(ValueError, match="Unsupported concentration unit\\."):
            Unit.parse_concentration('2 ' + invalid_unit)


    # ==========================================================================
    # Failure Case: Invalid argument value - too many slashes
    # ==========================================================================

    test_examples = ['2 mol/L/mol', 
                     '1 kg / 1 mmol / 12 mol',
                     '100 g //////////////// 100 g',
                     'This / is / not / a / valid / concentration!']
    for ex in test_examples:
        with pytest.raises(ValueError, match=f"Could not parse '{ex}'\\. "
                           "No more than one '/' should be used\\."):
            Unit.parse_concentration(ex)


    # ==========================================================================
    # Failure Case: Invalid argument value - invalid numerator
    # ==========================================================================

    # Sub-Case: Numerator cannot be parsed
    test_examples = ['#.....#/L', '0.5.a.5.5/mol', '---/1 g', '/12 mL']

    # Sub-Case: Numerator value is not a valid float
    test_examples += ['red mL/mol', '0.0.0 L/mL', 'inff mmol/mmol', '--1 mg/L',
                      'blue M', 'ThisIsBad mol/L']
    
    # Sub-Case: Numerator value is NaN.
    test_examples += ['NaN mol/1 L', 'NaN M']

    # Sub-Case: Numerator unit is not a valid unit
    test_examples += ['10 map/L', '0.5 mS/mol', '2.0001 F/mmol', '9.81 ggg/mol',
                      '888 M/L', '12 m/mol', '178 M/1 g']

    for ex in test_examples:
        with pytest.raises(ValueError, match=f"Could not parse '{ex}'\\. "
                            "Invalid numerator\\."):
            Unit.parse_concentration(ex)

    
    # ==========================================================================
    # Failure Case: Invalid argument value - invalid denominator
    # ==========================================================================

    # Sub-Case: Denominator cannot be parsed into a unit or a value & unit pair
    #           (cases of invalid denominator units without numbers are included
    #            here).
    test_examples = ['10 mol/', '2 g/None', '12 mL/AA', '5 g/----', '65 g/GGG',
                     '31 mol/M', '15 g/m', '4968 mmol/M']

    # Sub-Case: Denominator value is not a valid float.
    test_examples += ['8 mL/. mol', '1 L/0.0.0 mL', '4 mmol/inff mmol', 
                      '2mg/--1 L', '7 kL/## mol', '2 g / _____ g','1 L/yeesh g']
    
    # Sub-Case: Denominator value is NaN.
    test_examples += ['1 mol/NaN L']

    # Sub-Case: Denominator unit is not a valid unit (only cases with numbers in
    #           the denominator are included here).
    test_examples += ['1 g/2 ya', '1 mol/3 1231.2', '1 L/4 ______', '1 ug/10 A',
                      '12 mmol/2 M', '1 mmol/1 m']

    for ex in test_examples:
        with pytest.raises(ValueError, match=f"Could not parse '{ex}'\\. "
                            "Invalid denominator\\."):
            Unit.parse_concentration(ex)

    # Sub-Case: Denominator value is zero
    for num_unit, denom_unit in product(test_base_units, repeat=2):
        ex = '1 ' + num_unit + '/0 ' + denom_unit
        with pytest.raises(ValueError, match=f"Could not parse '{ex}'\\. "
                            "Denominator quantity cannot be zero\\."):
            Unit.parse_concentration(ex)


    # ==========================================================================
    # Failure Case: Invalid argument values - concentration is NaN
    # ==========================================================================

    for ex in ['inf mol/inf L', '-inf g/ inf mmol', '-inf L/-inf L']:
        with pytest.raises(ValueError, match=f"Could not parse '{ex}'\\. "
                            "Resulting concentration was NaN\\."):
            Unit.parse_concentration(ex)

    # ==========================================================================
    # Success Case: 'value concentration_unit'
    # ==========================================================================

    space_list = [' ' * i for i in range(5)]
    permutations = product(['','-'], test_values + ['0', 'inf '], space_list, 
                           ['M', 'm'])
    
    for sign, val, spaces, unit in permutations:
        # Construct examples with varying amounts of whitespace between the
        # value and the unit
        test_ex = f"{sign}{val}{spaces}{unit}"
        
        expected_value = float(sign + val) * (0.001 if unit == 'm' else 1)

        # Test varying amounts of external whitespace
        for pattern in test_whitespace_patterns:
            test_ex = pattern.replace('e', test_ex)

            value, num_unit, denom_unit = Unit.parse_concentration(test_ex)
            
            # If the input units are molality ('m'), then the output denom unit
            # must be scaled down by 1000 to match the returned units. Otherwise, 
            # the input value and returned value should match. 
            # 
            # To clarify the above, molality or 'm' means 'moles per kilogram'. 
            # Thus, a '2 m' concentration means the following:
            #
            #    2 m -> 2 mols per kg -> 0.002 mols per g
            #
            # Because Unit.parse_concentration() returns everything in base
            # units, the value needs to be scaled down from mol/kg to mol/g.
            assert expected_value == value
            assert 'mol' == num_unit
            assert ('L' if unit == 'M' else 'g') == denom_unit 


    # ==========================================================================
    # Success Case: 'value weight/volume%'
    # ==========================================================================

    # Create list of the input 'unit' as well as the expected numerator and 
    # denominator units for the output.
    unit_tuples = [('%w/w', 'g', 'g'), 
                   ('%v/v', 'L', 'L'), 
                   ('%w/v', 'g', 'L')]
    
    spaces_list = [" " * i for i in range(3)]

    # Create an iterable for all the permutations that will be tested. These
    # permutations include:
    #  - Sign: +/-
    #  - Value: Various float values
    #  - Number of Spaces: The space between the value and the weight/volume
    #                      percentage.
    #  - Unit Tuples: The three supported weight/volume percentages
    permutations = product(['','-'], test_values, spaces_list, unit_tuples)
    
    # Iterate through all permutations
    for sign, val, spaces, unit_tuple in permutations:
        # Unpack the unit tuple
        input_unit, expected_num_unit, expected_denom_unit = unit_tuple

        # Construct examples with varying amounts of whitespace between the
        # value and the unit
        test_ex = f"{sign}{val}{spaces}{input_unit}"

        expected_value = float(sign + val) * 0.01
        # TODO: Remove this quick-correction for %w/v
        if input_unit == '%w/v':
            expected_value *= 1000
        expected_value = pytest.approx(expected_value, rel=1e-24)

        # Test varying amounts of external whitespace
        for pattern in test_whitespace_patterns:
            test_ex = pattern.replace('e', test_ex)
            value, num_unit, denom_unit = Unit.parse_concentration(test_ex)

            assert expected_value == value
            assert expected_num_unit == num_unit
            assert expected_denom_unit == denom_unit

    
    # ==========================================================================
    # Success Case: 'value unit/unit'
    # ==========================================================================

    spaces_list = [" " * i for i in range(3)]

    # For performance reasons, the permutations will be broken up into two
    # categories:
    #   1) Whitespace parsing testing
    #   2) Value parsing testing

    # For the first set, a limited number of values will be tested, just enough
    # to cover the various ways the numbers would be written, and the units will
    # always be the same.

    # For the second category, only one whitespace pattern will be used, and a
    # larger set of values & units will be tested.

    # Create an iterable for all the permutations that will be tested. These
    # permutations include:
    #  - Sign: +/-
    #  - Value: Values with different lexical formats
    #  - Spaces 1: # of spaces between the value and the numerator unit
    #  - Spaces 2: # of spaces between the numerator unit and the '/', and 
    #              between the '/' and the denominator unit.
    #  - Pattern: The external whitespace surrounding the rest of the test 
    #             example.
    permutations = product(['','-'], ['1', '.24', '10.', '9.9', 'inf '], 
                           spaces_list, spaces_list, test_whitespace_patterns)

    # Iterate through all formatting permutations
    for sign, val, spaces_1, spaces_2, pattern in permutations:
        # Construct examples with varying amounts of whitespace between the
        # various parts of the concentration string
        #  E.g. '-' + '1' + '  ' + 'mol' + '' + '/' + '' + 'L' -> '-1  mol/L'
        test_ex = f"{sign}{val}{spaces_1}{'mol'}{spaces_2}"\
                  f"/{spaces_2}{'L'}"
        pattern.replace('e', test_ex)

        # Parse the expected result as a float (prefixes are set to 1 here)
        expected_value = float(sign + val)

        # Get the actual result of a call to parse_concentration() on the test
        # example
        value, num_unit, denom_unit = Unit.parse_concentration(test_ex)

        assert expected_value == value
        assert 'mol' == num_unit 
        assert 'L' == denom_unit

    # Create an iterable for all the permutations that will be tested. These
    # permutations include:
    #  - Sign: +/-
    #  - Value: Various test values that cover possible types of floats
    #  - Num Unit: Various possible units for the numerator
    #  - Denom Unit: Various possivle units for the denominator
    permutations = product(['','-'], test_values + ['0', 'inf '], 
                           test_units, test_units)

    # Iterate through all value/unit permutations
    for sign, val, num_unit, denom_unit in permutations:
          
        # Construct the test example from the various pieces
        test_ex = f"{sign}{val} {num_unit}/{denom_unit}"

        # Get the base unit and multiplier for the numerator and denominator
        expected_num_unit, num_mult = test_units_bases_and_mults[num_unit]
        expected_denom_unit, denom_mult = test_units_bases_and_mults[denom_unit]

        # Compute the expected result for the value based on the supplied
        # prefixes 
        expected_value = float(sign + val) * num_mult / denom_mult

        # Get the actual result of a call to parse_concentration() on the test
        # example
        value, num_unit, denom_unit = Unit.parse_concentration(test_ex)

        # TODO: [BUG] Come back and fix precision issue here.
        assert expected_value == pytest.approx(value, rel=1e-10, abs=1e-10)
        assert expected_num_unit == num_unit 
        assert expected_denom_unit == denom_unit


    # ==========================================================================
    # Success Case: 'value unit/value unit'
    # ==========================================================================

    spaces_list = [" " * i for i in range(3)]

    # Create an iterable for all the permutations that will be tested. These
    # permutations include:
    #  - Sign: +/-
    #  - Value: Values with different lexical formats
    #  - Spaces 1: # of spaces between the values and their units
    #  - Spaces 2: # of spaces between the numerator unit and the '/', and 
    #              between the '/' and the denominator unit.
    permutations = product(['','-'], ['1', '.25', '10.', '0.05', 'inf '], 
                           spaces_list, spaces_list, test_whitespace_patterns)

    # Iterate through all formatting permutations
    for sign, val, spaces_1, spaces_2, pattern in permutations:
        # Construct examples with varying amounts of whitespace between the
        # various parts of the concentration string
        #  E.g. '-' + '1' + ' ' + 'mol' + '' + '/' + '' + '0.24' + ' ' + 'L' 
        #       '-1 mol/0.24 L'
        test_ex = f"{sign}1{spaces_1}mol{spaces_2}"\
                  f"/{spaces_2}{val}{spaces_1}L"
        pattern.replace('e', test_ex)

        # Parse the expected result as a float (prefixes are set to 1 here)
        expected_value = 1 / float(sign + val)

        # Get the actual result of a call to parse_concentration() on the test
        # example
        value, num_unit, denom_unit = Unit.parse_concentration(test_ex)

        assert expected_value == value
        assert 'mol' == num_unit 
        assert 'L' == denom_unit

    # Create an iterable for all the permutations that will be tested. These
    # permutations include:
    #  - Sign: +/-
    #  - Num Value: Various test values for the numerator
    #  - Num Unit: Various possible units for the numerator
    #  - 
    #  - Denom Unit: Various possivle units for the denominator
    # 
    # NOTE: Sub-sampling was added due to increase unit test speed.
    permutations = product(['','-'], test_values[::4] + ['0', 'inf '], test_units[::4], 
                           test_values[::2] + ['inf '], test_units)

    # Iterate through all value/unit permutations
    for sign, num_val, num_unit, denom_val, denom_unit in permutations:
        # Skip this case; it is a failure case
        if num_val == 'inf ' and denom_val == 'inf ':
            continue

        # Construct the test example from the various pieces
        test_ex = f"{sign}{num_val} {num_unit}/{denom_val} {denom_unit}"

        # Get the base unit and multiplier for the numerator and denominator
        expected_num_unit, num_mult = test_units_bases_and_mults[num_unit]
        expected_denom_unit, denom_mult = test_units_bases_and_mults[denom_unit]

        # Compute the expected result for the value based on the supplied
        # values and prefixes 
        expected_value = float(sign + num_val) * num_mult 
        expected_value /= float(denom_val) * denom_mult

        # Get the actual result of a call to parse_concentration() on the test
        # example
        value, num_unit, denom_unit = Unit.parse_concentration(test_ex)

        # TODO: [BUG] Come back and fix precision issue here.
        assert expected_value == pytest.approx(value, rel=1e-10, abs=1e-10)
        assert expected_num_unit == num_unit 
        assert expected_denom_unit == denom_unit

    # ==========================================================================
    # Success Case: Hand-picked examples
    # ==========================================================================

    examples = [
        ('10 M', 10.0, 'mol', 'L'),
        ('10 mM', 0.01, 'mol', 'L'),
        ('50 m', 0.05, 'mol', 'g'),
        ('50 km', 50, 'mol', 'g'),
        ('0 M', 0, 'mol', 'L'),
        ('0 m', 0, 'mol', 'g'),
        
        ('1 %w/v', 10.0, 'g', 'L'),
        ('25 %v/v', 0.25, 'L', 'L'),
        ('2 %w/w', 0.02, 'g', 'g'),
        ('0 %w/v', 0, 'g', 'L'),
        
        ('0.1 mol/L', 0.1, 'mol', 'L'),
        ('7 g/g', 7, 'g', 'g'),
        ('0.1 kmol/mL', 1e5, 'mol', 'L'),
        ('0.4 mL/mol', 0.0004, 'L', 'mol'),
        ('36 mg/ug', 36000, 'g', 'g'),
        ('0.1 kg/kmol', 0.1, 'g', 'mol'),
        ('0 g/L', 0, 'g', 'L'),
        ('inf mol/mol', float('inf'), 'mol', 'mol'),

        ('1 mol/1 L', 1, 'mol', 'L'),
        ('0.5 mol/2 L', 0.25, 'mol', 'L'),
        ('3 dag/0.4 mol', 75, 'g', 'mol'),
        ('0 g/1 L', 0, 'g', 'L'),
        ('0 g/inf L', 0, 'g', 'L'),
        ('inf mol/1 mol', float('inf'), 'mol', 'mol')
    ]

    for ex in examples:
        value, num_unit, denom_unit = Unit.parse_concentration(ex[0])
        assert ex[1] == value
        assert ex[2] == num_unit
        assert ex[3] == denom_unit

def test_Unit_convert_to_storage():
    """
    Unit Test for `Unit.convert_to_storage()`
    
    This unit test checks for the following failure cases:
    - Invalid argument types result in raising a `TypeError`
    - Invalid value for 'unit' argument results in raising a `ValueError`
      - Case: A string that does not parse correctly as a base or prefixed unit.
        - E.g. 'abba' or 'mA'
      - Case: A string that parses as a non-molar and non-volume unit.
        - E.g. 'g' or 'mg'
    
    NOTE: Currently, any float value is supported for the 'value' argument, 
    including NaN, so there are no failure cases for a correctly-typed 
    'value' argument.

    This unit test checks for the following success cases:
    - Unit argument is the base unit 'mol'
    - Unit argument is a prefixed molar unit (e.g. 'mmol')
    - Unit argument is the base unit 'L'
    - Unit argument is a prefixed volume unit (e.g. 'mL')
    """

    # ==========================================================================
    # Failure Case: Invalid argument type
    # ==========================================================================

    for non_float in [None, '', '1', [1], (1,), {}]:
        with pytest.raises(TypeError, match="Value must be a float\\."):
            Unit.convert_to_storage(non_float, 'L')

    for non_str in [None, False, 1, ['1'], ('1',), {}]:
        with pytest.raises(TypeError, match="Unit must be a str\\."):
            Unit.convert_to_storage(1, non_str)

    
    # ==========================================================================
    # Failure Case: Invalid argument value - unit
    # ==========================================================================

    # Case: Argument 'unit' is an invalid unit
    for invalid_unit in test_invalid_units:
        with pytest.raises(ValueError, match=f"Invalid unit '{invalid_unit}'\\.$"):
            Unit.convert_to_storage(1, invalid_unit)

    # Case: Argument 'unit' is a non-molar and non-volume unit
    for prefix in test_prefixes:
        invalid_unit = prefix + 'g'
        with pytest.raises(ValueError, match=f"Invalid unit '{invalid_unit}'\\."
                                      " Unit must refer to moles or volume."):
            Unit.convert_to_storage(1, invalid_unit)

    
    # ==========================================================================
    # Success Cases 
    # ==========================================================================

    base_units = ['mol', 'L']
    values = [1, 5.789, -12, -4.5, -0.000001, 0.0, -0.0, 
              float('inf'), float('-inf')]
    prefix_mults = zip(test_prefixes, test_prefix_multipliers)
    permutations = product(base_units, values, prefix_mults)

    # TODO: Add mocking to remove Unit.convert_prefix_to_multiplier() dependency
    storage_mults = {
        'mol': Unit.convert_prefix_to_multiplier(config.moles_storage_unit[:-3]),
        'L': Unit.convert_prefix_to_multiplier(config.volume_storage_unit[:-1])
    }

    for base_unit, value, (prefix, mult) in permutations:
        test_unit = prefix + base_unit
        
        expected_value = value * mult / storage_mults[base_unit]
        result = Unit.convert_to_storage(value, test_unit)
        assert expected_value == pytest.approx(result, rel=1e-24)

    # NaN == NaN returns false, so that needs a separate check
    assert math.isnan(Unit.convert_to_storage(float('nan'), 'mol'))
    assert math.isnan(Unit.convert_to_storage(float('nan'), 'L'))

def test_Unit_convert_from_storage():
    """
    Unit test for `Unit.convert_from_storage()`

    This unit test checks the following failure scenarios:
    - Invalid argument types result in raising a `TypeError`
    - Invalid value for 'unit' argument results in raising a `ValueError`
      - Case: A string that does not parse correctly as a base or prefixed unit.
        - E.g. 'abba' or 'mA'
      - Case: A string that parses as a non-molar and non-volume unit.
        - E.g. 'g' or 'mg'

    NOTE: Currently, any float value is supported for the 'value' argument, 
    including NaN, so there are no failure cases for a correctly-typed 
    'value' argument.

    This unit test checks for the following success cases:
    - Unit argument is the base unit 'mol'
    - Unit argument is a prefixed molar unit (e.g. 'mmol')
    - Unit argument is the base unit 'L'
    - Unit argument is a prefixed volume unit (e.g. 'mL')
    """
    
    # ==========================================================================
    # Failure Case: Invalid argument type
    # ==========================================================================

    for non_float in [None, '', '1', [1], (1,), {}]:
        with pytest.raises(TypeError, match="Value must be a float\\."):
            Unit.convert_from_storage(non_float, 'L')

    for non_str in [None, False, 1, ['1'], ('1',), {}]:
        with pytest.raises(TypeError, match="Unit must be a str\\."):
            Unit.convert_from_storage(1, non_str)

    # ==========================================================================
    # Failure Case: Invalid argument value - unit
    # ==========================================================================

    # Case: Argument 'unit' is an invalid unit
    for invalid_unit in test_invalid_units:
        with pytest.raises(ValueError, match=f"Invalid unit '{invalid_unit}'\\.$"):
            Unit.convert_from_storage(1, invalid_unit)

    # Case: Argument 'unit' is a non-molar and non-volume unit
    for prefix in test_prefixes:
        invalid_unit = prefix + 'g'
        with pytest.raises(ValueError, match=f"Invalid unit '{invalid_unit}'\\."
                                      " Unit must refer to moles or volume."):
            Unit.convert_from_storage(1, invalid_unit)

    # ==========================================================================
    # Success Cases 
    # ==========================================================================

    base_units = ['mol', 'L']
    values = [1, 5.789, -12, -4.5, -0.000001, 0.0, -0.0, 
              float('inf'), float('-inf')]
    prefix_mults = zip(test_prefixes, test_prefix_multipliers)
    permutations = product(base_units, values, prefix_mults)

    # TODO: Add mocking to remove Unit.convert_prefix_to_multiplier() dependency
    storage_mults = {
        'mol': Unit.convert_prefix_to_multiplier(config.moles_storage_unit[:-3]),
        'L': Unit.convert_prefix_to_multiplier(config.volume_storage_unit[:-1])
    }

    for base_unit, value, (prefix, mult) in permutations:
        test_unit = prefix + base_unit
        
        expected_value = value * storage_mults[base_unit] / mult
        result = Unit.convert_from_storage(value, test_unit)

        # TODO: [BUG] Come back and fix precision issue here.
        assert result == pytest.approx(expected_value, rel=1e-10, abs=1e-10)

    # NaN == NaN returns false, so that needs a separate check
    assert math.isnan(Unit.convert_from_storage(float('nan'), 'mol'))
    assert math.isnan(Unit.convert_from_storage(float('nan'), 'L'))

def test_Unit_convert_from_storage_to_standard_format(salt, water, 
                                                      invalid_substance):
    """
    Unit Test for `Unit.convert_from_storage_to_standard_format()`

    This unit test checks for the following failure cases:
    - Invalid argument types result in raising a `TypeError`
    - Invalid argument values result in raising a `ValueError`
      - Case: Substance argument is neither solid nor liquid.

    NOTE: Currently, any float value is supported for the 'value' argument, 
    including NaN, so there are no failure cases for a correctly-typed 
    'value' argument.

    NOTE: This function uses the substance parameter to convert to non-storage
    units. Thus, 

    This unit test checks for the following success cases:
    - Solid and liquid substances
    - Various prefixed and unprefixed units

    Each success case is tested to ensure the value and unit returned match
    those that are expected.
    """

    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================
    
    for non_substance in [None, False, 1, '1', [1,], (salt, water), {}]:
        with pytest.raises(TypeError, match="Invalid type for substance\\."):
            Unit.convert_from_storage_to_standard_format(non_substance, 1)
    
    for non_float in [None, '1', salt, (1,), [water], {}]:
        with pytest.raises(TypeError, match="Quantity must be a float\\."):
            Unit.convert_from_storage_to_standard_format(salt, non_float)


    # ==========================================================================
    # Failure Case: Invalid argument value - substance type
    # ==========================================================================
    
    with pytest.raises(ValueError, match="Invalid subtype for substance\\."):
        Unit.convert_from_storage_to_standard_format(invalid_substance, 1)


    # ==========================================================================
    # Success Cases
    # ==========================================================================
    
    examples= [
        ((salt, 1), (58.4428, 'ug')),
        ((salt, 10), (584.428, 'ug')),
        ((salt, 100), (5.84428, 'mg')),
        ((salt, 1000), (58.4428, 'mg')),
        ((salt, 1e6), (58.4428, 'g')),

        ((salt, 0.1), (5.84428, 'ug')),
        ((salt, 0.01), (584.428, 'ng')),
        ((salt, 0.001), (58.4428, 'ng')),
        ((salt, 0.0001), (5.84428, 'ng')),
        ((salt, 0.00001), (0.584428, 'ng')),

        ((water, 1), (18.0153, 'nL')),
        ((water, 10), (180.153, 'nL')),
        ((water, 100), (1.80153, 'uL')),
        ((water, 1000), (18.0153, 'uL')),
        ((water, 1e6), (18.0153, 'mL')),
        ((water, 1e9), (18.0153, 'L')),

        ((water, 0.1), (1.80153, 'nL')),
        ((water, 0.01), (0.180153, 'nL')),
        ((water, 0.001), (0.0180153, 'nL')),
    ]

    for ex, (expected_value, expected_unit) in examples:
        results = Unit.convert_from_storage_to_standard_format(ex[0], ex[1])

        assert results[0] == pytest.approx(expected_value, rel=1e-24)

        # The second case here handles the equivalent prefixes of 'u' and 'µ'
        # TODO: Improve the generality of this assert statement (i.e. make this
        #       less hacky)
        assert results[1] == expected_unit or \
                (results[1][0] == 'µ'and 'u' + results[1][1:] == expected_unit)
        
def test_Unit_get_human_readable_unit():
    """
    Unit Test for `Unit.get_human_readable_unit()`
    
    This unit test checks the following failure scenarios:
    - Invalid argument types raise a `TypeError`.
    - 
    """
    # TODO: Need to finish this last unit test


