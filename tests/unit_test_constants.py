
epsilon = 1e-3

# Test examples should be inserted at the location of the 'e' character. 
#
# Variations for whitespace patterns include:
# - No whitespace
# - Single space/tab/newline character on the left
# - Single space/tab/newline character on the right
# - Single space/tab/newline character on both sides
# - Multiple space/tab/newline characters on both side
# - Mixed space/tab/newline chracters throughout the string
test_whitespace_patterns = ['e', ' e', 'e ', ' e ', '   e   ',
                            'e\t', '\te', '\te\t', '\t\t\te\t\t\t',
                            'e\n', '\ne', '\ne\n', '\n\n\ne\n\n\n',
                            'e \t\n', ' \t\ne', '  \t\t\n\ne\n\n\t\t  ']

# Variations for test names include:
# - Lowercase alphabetical string
# - Lowercase alphanumeric string
# - Mixed-case alphanumeric string 
# - Mixed-case string with special characters
# - Mixed-case string with special characters and spaces
# - String with only special characters
test_names = ['container', 'plate', 'substance', 'recipe'
              'container2', 'plate78', '2substance', 'rec1pe'
              'otherContainer2', 'Plate8', '5UB5TANcE', 'ReCiPe15'
              'other_Container3', 'my.Container/12'
              'the Container #overThere', 
              '&*&*&*&', '....', "######"]

# Variations for test values include single/multidigit integers, and
# single/multidigit decimals
test_values = ['1', '20', '300', '4000', '56', '789',
                '0.1', '0.001', '0.5', '1.5', '200.5', '0.0000001',
                '.1', '.0089',
                '7.', '2562.'
              ]

test_positive_numbers = [float(test_value) for test_value in test_values]

test_prefixes = ['', 'm', 'da', 'u', 'k', 'n']
"""
This list contains the selected prefixes that are used for testing.
"""

test_prefix_multipliers = [1, 1e-3, 10, 1e-6, 1000, 1e-9]
"""
This contains values corresponding to the positionally matching entries of 
test_prefixes.
"""

test_base_units = ['L', 'mol', 'g']
"""
This list contains the base units that are used for testing.
"""

test_invalid_base_units = ['K', 'C', 'F', 'T', 'H', 'asdf', 'mool']

# Create all permutations of the above prefixes and base units
test_units = []
test_units_bases_and_mults = {}
for prefix, mult in zip(test_prefixes, test_prefix_multipliers):
    for base_unit in test_base_units:
        test_units.append(prefix + base_unit)
        test_units_bases_and_mults[test_units[-1]] = (base_unit, mult)

# Create all permutations of the above prefixes and invalid base units
test_invalid_units = []
for prefix in test_prefixes:
    for base_unit in test_invalid_base_units:
        test_invalid_units.append(prefix + base_unit)
test_invalid_units.append('')

# Create all volume units using the above prefixes
test_volume_units = []
for prefix in test_prefixes:
    test_volume_units.append(prefix + 'L')

# Create all permutations of the above test values & volume units
test_volumes = []
test_positive_volumes = []
test_negative_volumes = []
for value in test_values:
    for unit in test_volume_units:
        ex_space = value + ' ' + unit
        ex_no_space = value + unit

        test_volumes.append(ex_space)
        test_volumes.append(ex_no_space)
        test_positive_volumes.append(ex_space)
        test_positive_volumes.append(ex_no_space)

        ex_space = '-' + ex_space
        ex_no_space = '-' + ex_no_space

        test_volumes.append(ex_space)
        test_volumes.append(ex_no_space)
        test_negative_volumes.append(ex_space)
        test_negative_volumes.append(ex_no_space)

test_zero_volumes = []

# Add zero cases (should only be added to overall volumes)
for unit in test_volume_units:
    test_volumes.append('0 ' + unit)
    test_volumes.append('0' + unit)
    test_volumes.append('-0 ' + unit)
    test_volumes.append('-0' + unit)
    test_zero_volumes.append('0 ' + unit)
    test_zero_volumes.append('0' + unit)
    test_zero_volumes.append('-0 ' + unit)
    test_zero_volumes.append('-0' + unit)

# Add +/- infinity cases (should always have spaces)
for unit in test_volume_units:
    test_volumes.append('inf ' + unit)
    test_volumes.append('-inf ' + unit)
    test_positive_volumes.append('inf ' + unit)
    test_negative_volumes.append('-inf ' + unit)


# Create all permutations of the above test values and test units
test_quantities = []
test_positive_quantities = []
test_negative_quantities = []
for value in test_values:
    for unit in test_units:
        ex_space = value + ' ' + unit
        ex_no_space = value + unit

        test_quantities.append(ex_space)
        test_quantities.append(ex_no_space)
        test_positive_quantities.append(ex_space)
        test_positive_quantities.append(ex_no_space)

        ex_space = '-' + ex_space
        ex_no_space = '-' + ex_no_space

        test_quantities.append(ex_space)
        test_quantities.append(ex_no_space)
        test_negative_quantities.append(ex_space)
        test_negative_quantities.append(ex_no_space)

test_zero_quantities = []

# Add zero cases (should only be added to overall volumes)
for unit in test_units:
    test_quantities.append('0 ' + unit)
    test_quantities.append('0' + unit)
    test_quantities.append('-0 ' + unit)
    test_quantities.append('-0' + unit)
    test_zero_quantities.append('0 ' + unit)
    test_zero_quantities.append('0' + unit)
    test_zero_quantities.append('-0 ' + unit)
    test_zero_quantities.append('-0' + unit)

# Add +/- infinity cases (should always have spaces)
for unit in test_units:
    test_quantities.append('inf ' + unit)
    test_quantities.append('-inf ' + unit)
    test_positive_quantities.append('inf ' + unit)
    test_negative_quantities.append('-inf ' + unit)



# Variations for invalid values include:
# - Non-float-parseable alphabetical strings
# - Non-float-parseable alphanumeric strings
# - Multiple decimal places
# - Single isolated negative sign
# - Multiple or missplaced negative signs
test_invalid_values = ['max_volume', 'aaa', 'test_volume',
                        '10a0', 'a12', 'zyys234', 'sb129',
                        '0.0.1', '1.1.1.1.1.1', '0..1',
                        '-',
                        '--1', '1-', '23-43']

test_invalid_volumes = []
for value in test_invalid_values:
    for unit in test_volume_units:
        ex_space = value + ' ' + unit
        ex_no_space = value + unit
        test_invalid_volumes.append(ex_space)
        test_invalid_volumes.append(ex_no_space)




# Variations for non-parseable test quantities include:
# - Alphabetical characters (gibberish)
# - Valid unit (base unit or 'M') 
# - Valid unit (prefixed unit) 
# - Valid value (integer) 
# - Valid value (decimal) 
# - Valid value (limit)
# - Invalid value (integer)
# - Invalid value (decimal)
# - Invalid value (limit)
test_non_parseable_quantities = ['',
                                'asdf', 'feefiefoefum', 'foobar',
                                'L', 'g', 'mol', 'M',
                                'mL', 'mg', 'umol', 'kmol', 'kL', 'uL', 'mM',
                                '1', '2', '2000', '40', '3000', '192837465', '0'
                                '0.1', '0.254', '12.345', '98890.23183', '0.00002',
                                '-111-', '-', '--0512', '---1024',
                                '1.1.1', '-.', '-.-', '1-.-1', '092.-09',
                                'inf', 'nan'
                                ]


if __name__ == "__main__":
    print("Test Names:\n-------------------")
    print(test_names)
    print("\n\n")

    print("Test Units:\n-------------------")
    print(test_units)
    print("\n\n")

    print("Test Volume Units:\n---------------------")
    print(test_volume_units)
    print("\n\n")

    print("Test Volumes:\n-------------------")
    print(test_volumes)
    print("\n\n")

    print("Test Positive Volumes:\n------------------------")
    print(test_positive_volumes)
    print("\n\n")

    print("Test Negative Volumes:\n------------------------")
    print(test_negative_volumes)
    print("\n\n")

    print("Test Invalid Volumes:\n------------------------")
    print(test_invalid_volumes)
    print("\n\n")

