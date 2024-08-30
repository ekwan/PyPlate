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