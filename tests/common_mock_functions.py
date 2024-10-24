from pyplate import Unit

# Define mock quantity parsing
# - Units are not checked to ensure they parse correctly. This is to allow 
#   higher-level unit tests to reach typically-impossible unit tests.
# - Quantities that would normally fail to parse instead return a default 
#   value.
def mock_parse_quantity(quantity : str):
    # Ensure that the quantity is a string
    if not isinstance(quantity, str):
        raise TypeError("Quantity must be a string.")

    # Match the primary regular expression against the quantity string
    match = Unit._PRIMARY_QUANTITY_PATTERN_COMPILED.match(quantity)

    # If matching fails, try to match with the secondary regular expression
    if not match:
        match = Unit._SECONDARY_QUANTITY_PATTERN_COMPILED.match(quantity)

        # If matching fails again, instead of erroring, return a default 
        # quantity
        if not match:
            return 1, 'L'
        
    # Extract the value-unit pair from the capture groups
    value, unit = match.group(1), match.group(2)

    return float(value), unit


# Define mock concentration parsing
# - Units are not checked to ensure they parse correctly. This is to allow 
#   higher-level unit tests to reach typically-impossible unit tests.
# - Denominators are assumed to only be units. Denominators with values before 
#   the unit are not handled correctly.
# - Concentrations that would normally fail to parse instead return a default 
#   value.
def mock_parse_concentration(conc: str):
    # Ensure that the quantity is a string
    if not isinstance(conc, str):
        raise TypeError("Concentration must be a string.")

    split_res = conc.split('/')

    # If concentration has more than one '/', return a default concentration.
    if len(split_res) > 2:
        return 1, 'mol', 'L'
    
    # If concentration has only one '/', check if it is a molarity/molality. If 
    # so, convert it to fractional units. Otherwise, instead of erroring, return
    # a default concentration.
    if len(split_res) == 1:
        if conc.strip().endswith('M'):
            conc = conc.strip()[:-1] + 'mol/L'
            split_res = conc.split('/')
        elif conc.strip().endswith('m'):
            conc = conc.strip()[:-1] + 'mol/kg'
            split_res = conc.split('/')
        else:
            return 1, 'mol', 'L'

    numerator, denominator = split_res

    # Match the primary regular expression against the numerator string
    match = Unit._PRIMARY_QUANTITY_PATTERN_COMPILED.match(numerator)

    # If matching fails, try to match with the secondary regular expression
    if not match:
        match = Unit._SECONDARY_QUANTITY_PATTERN_COMPILED.match(numerator)

        # If matching fails again, instead of erroring, return a default 
        # concentration
        if not match:
            return 1, 'mol', 'L'

    # Extract the value-unit pair from the capture groups
    value, numerator_unit = match.group(1), match.group(2)

    denominator_unit = denominator.strip()

    return float(value), numerator_unit, denominator_unit