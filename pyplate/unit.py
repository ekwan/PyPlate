from typing import Tuple

import math
import re

from pyplate.config import config
from pyplate.substance import Substance


class Unit:
    """
    Provides unit conversion utility functions.
    """

    BASE_UNITS = ["g", "L", "mol"]
    
    BASE_UNITS_PLUS_CONCENTRATION = BASE_UNITS.copy()
    BASE_UNITS_PLUS_CONCENTRATION.append("M")

    PREFIXES = {'n': 1e-9, 
                'u': 1e-6, 'µ': 1e-6, 
                'm': 1e-3, 
                'c': 1e-2, 
                'd': 1e-1, 
                '': 1, 
                'da': 1e1, 
                'k': 1e3, 
                'M': 1e6}
    
    _PREFIX_LOOKUP = {v: k for k, v in PREFIXES.items()}

    # The primary regular expression for parsing quantities can be broken down into the following pieces:
    #
    #  ^\s* -> Matching must start at the beginning of the string, and allows any 
    #          amount of whitespace characters before the start of the quantity.
    #
    # ([-\d\.]+) -> First capture group; captures value half of the quantity.
    #                       
    #                       Matches one or more digits, decimal point characters,
    #                       or hypen (minus sign) characters.
    #
    # \s* -> Between the first and second catpure groups, allow for zero or more 
    #        whitespace characters.
    #
    # ([a-zA-Z]+) -> Second capture group; captures the unit (prefix + base unit)
    #                half of the quantity. 
    #   
#                       Matches one or more alphabetical characters.
    #
    # \s*$ -> Requires that matching include the end of the string, and allows 
    #         any amount of whitespace between the unit and the end of the string.
    _PRIMARY_QUANTITY_PATTERN = r'^\s*([-\d\.]+)\s*([a-zA-Z]+)\s*$'
    _PRIMARY_QUANTITY_PATTERN_COMPILED = re.compile(_PRIMARY_QUANTITY_PATTERN)

    # The secondary regular expression for parsing quantities can be broken down into the following pieces:
    #
    #  ^\s* -> Matching must start at the beginning of the string, and allows any
    #          amount of whitespace before the start of the quantity.
    #
    # ([^\s]+) -> First capture group; captures the value half of the quantity. 
    #             
    #               Matches one or more non-whitespace characters. 
    #
    # \s+ -> Between the second catpure group, allow for one or more whitespaces.
    #           NOTE: Unlike the primary regular expression, there MUST be at least
    #           one whitespace in between the value and unit.
    #
    # ([a-zA-Z]+) -> Second capture group; captures the unit (prefix + base
    #                unit). 
    # 
    #                   Matches one or more alphabetical characters.
    #
    # \s*$ -> Matching must end at the end of the string, and allows any amount
    #         of whitespace between the unit and the end of the string.
    _SECONDARY_QUANTITY_PATTERN = r'^\s*([^\s]+)\s+([a-zA-Z]+)\s*$' 
    _SECONDARY_QUANTITY_PATTERN_COMPILED = re.compile(_SECONDARY_QUANTITY_PATTERN)

    @staticmethod
    def convert_prefix_to_multiplier(prefix: str) -> float:
        """
        Converts an SI prefix into a multiplier.

        Examples: "m" -> 1e-3, "u" -> 1e-6

        Arguments:
            prefix:

        Returns:
             Multiplier (float)

        """
        # Check type of prefix argument
        if not isinstance(prefix, str):
            raise TypeError("SI prefix must be a string.")
        
        # If the prefix is support, return the associated multiplier
        if prefix in Unit.PREFIXES:
            return Unit.PREFIXES[prefix]
        
        # Otherwise, raise an error
        raise ValueError(f"Invalid prefix: {prefix}")
    
    @staticmethod
    def convert_multiplier_to_prefix(multiplier: float) -> str:
        """
        Converts multiplier into an SI prefix. Multipliers will be floored
        to the nearest power of ten for the conversion.

        Examples: 1e-3 -> 'm', 2.5e3 -> 1e3 -> 'k'

        Arguments:
            prefix:

        Returns:
             Multiplier (float)

        """
        # Check type of multiplier argument
        if not isinstance(multiplier, (float, int)):
            raise TypeError("Multiplier must be a number.")
        
        # Determine the nearest floored power of ten
        multiplier = 10 ** math.floor(math.log10(multiplier))

        if multiplier in Unit._PREFIX_LOOKUP:
            return Unit._PREFIX_LOOKUP[multiplier]
        raise ValueError(f"Invalid multiplier: {multiplier}")

    @staticmethod
    def parse_quantity(quantity: str) -> Tuple[float, str]:
        """

        Splits a quantity into a value and unit, converting any SI prefix.
        Example: '10 mL' -> (0.01, 'L')

        Arguments:
            quantity: Quantity to convert.

        Returns: A tuple of float and str. The float will be the parsed value
         and the str will be the unit ('L', 'mol', 'g', etc.).

        """
        
        # Ensure that the quantity is a string
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a string.")

        # Match the primary regular expression against the quantity string
        match = Unit._PRIMARY_QUANTITY_PATTERN_COMPILED.match(quantity)

        # If matching fails, try to match with the secondary regular expression
        if not match:
            match = Unit._SECONDARY_QUANTITY_PATTERN_COMPILED.match(quantity)

            # If matching fails again, fail to parse the quantity and raise a ValueError
            if not match:
                raise ValueError(f"Could not parse '{quantity}' into a valid value-unit pair.")
            
        # Extract the value-unit pair from the capture groups
        value, unit = match.group(1), match.group(2)

        # Attempt to parse the value as a float
        try:
            value = float(value)
        # Raise a ValueError if float-parsing fails
        except ValueError as exc:
            raise ValueError(f"Value '{value}' is not a valid float.") from exc
        
        if math.isnan(value):
            raise ValueError("'NaN' values are forbidden for quantities.")

        # Check to see if the extracted unit is a valid unit.
        for base_unit in Unit.BASE_UNITS_PLUS_CONCENTRATION:

            # Check if the unit ends with a base unit
            if unit.endswith(base_unit):
                # Set the prefix to the what precedes the base unit 
                prefix = unit[:-len(base_unit)]
                # Parse the prefix (will raise a ValueError if it fails)
                # and multiply the value by the associated multiplier
                # (e.g. m -> 1e-3)
                value = value * Unit.convert_prefix_to_multiplier(prefix)
                # Return the value and base unit
                return value, base_unit
            
        # If no base units matched the end of the unit string, the unit must
        # be invalid. Raise a ValueError stating as much.
        raise ValueError(f"Invalid unit '{unit}'.")

    @staticmethod
    def parse_concentration(concentration : str) -> Tuple[float, str, str]:
        """
        Parses concentration string to (value, numerator, denominator).
        Args:
            concentration: concentration, '1 M', '1 umol/uL', '0.1 umol/10 uL'

        Returns: Tuple of value, numerator, denominator. (0.01, 'mol', 'L')

        """
        if '/' not in concentration:
            if concentration[-1] == 'm':
                concentration = concentration[:-1] + 'mol/kg'
            elif concentration[-1] == 'M':
                concentration = concentration[:-1] + 'mol/L'
            else:
                raise ValueError("Only m and M are allowed as concentration units.")
        replacements = {'%v/v': 'L/L', '%w/w': 'g/g', '%w/v': config.default_weight_volume_units}
        if concentration[-4:] in replacements:
            concentration = concentration[:-4] + replacements[concentration[-4:]]
            numerator, denominator = map(str.split, concentration.split('/'))
            numerator[0] = float(numerator[0]) / 100  # percent
        else:
            numerator, denominator = map(str.split, concentration.split('/'))
        if len(numerator) < 2 or len(denominator) < 1:
            raise ValueError("Concentration must be of the form '1 umol/mL'.")
        try:
            numerator[0] = float(numerator[0])
            if len(denominator) > 1:
                numerator[0] /= float(denominator.pop(0))
        except ValueError as exc:
            raise ValueError("Value is not a float.") from exc
        units = ('mol', 'L', 'g')
        for unit in units:
            if numerator[1].endswith(unit):
                numerator[0] *= Unit.convert_prefix_to_multiplier(numerator[1][:-len(unit)])
                numerator[1] = unit
            if denominator[0].endswith(unit):
                numerator[0] /= Unit.convert_prefix_to_multiplier(denominator[0][:-len(unit)])
                denominator[0] = unit
        if numerator[1] not in ('mol', 'L', 'g') or denominator[0] not in ('mol', 'L', 'g'):
            raise ValueError("Concentration must be of the form '1 umol/mL'.")
        return round(numerator[0], config.internal_precision), numerator[1], denominator[0]

    @staticmethod
    def convert_from(substance: Substance, quantity: float, from_unit: str, to_unit: str) -> float:
        """
                    Convert quantity of substance between units.

                    Arguments:
                        substance: Substance in question.
                        quantity: Quantity of substance.
                        from_unit: Unit to convert quantity from ('mL').
                        to_unit: Unit to convert quantity to ('mol').

                    Returns: Converted value.

                """

        if not isinstance(substance, Substance):
            raise TypeError(f"Invalid type for substance, {type(substance)}")
        if not isinstance(quantity, (int, float)):
            raise TypeError("Quantity must be a float.")
        if not isinstance(from_unit, str) or not isinstance(to_unit, str):
            raise TypeError("Unit must be a str.")

        for suffix in ['L', 'g', 'mol']:
            if from_unit.endswith(suffix):
                prefix = from_unit[:-len(suffix)]
                quantity *= Unit.convert_prefix_to_multiplier(prefix)
                from_unit = suffix
                break
        else:  # suffix not found
            raise ValueError(f"Invalid unit {from_unit}")

        for suffix in ['L', 'g', 'mol']:
            if to_unit.endswith(suffix):
                prefix = to_unit[:-len(suffix)]
                to_unit = suffix
                break
        else:  # suffix not found
            raise ValueError(f"Invalid unit {to_unit}")

        result = None

        if to_unit == 'L':
            if from_unit == 'L':
                result = quantity
            elif from_unit == 'mol':
                # mol * g/mol / (g/mL)
                result_in_mL = quantity * substance.mol_weight / substance.density
                result = result_in_mL / 1000.
            elif from_unit == 'g':
                # g / (g/mL)
                result_in_mL = quantity / substance.density
                result = result_in_mL / 1000
        elif to_unit == 'mol':
            if from_unit == 'L':
                value_in_mL = quantity * 1000.  # L * mL/L
                # mL * g/mL / (g/mol)
                result = value_in_mL * substance.density / substance.mol_weight
            elif from_unit == 'mol':
                result = quantity
            elif from_unit == 'g':
                # g / (g/mol)
                result = quantity / substance.mol_weight
        elif to_unit == 'g':
            if from_unit == 'L':
                # L * (1000 mL/L) * g/mL
                result = quantity * 1000. * substance.density
            elif from_unit == 'mol':
                # mol * g/mol
                result = quantity * substance.mol_weight
            elif from_unit == 'g':
                result = quantity

        assert result is not None, f"{substance} {quantity} {from_unit} {to_unit}"

        return result / Unit.convert_prefix_to_multiplier(prefix)

    @staticmethod
    def convert(substance: Substance, quantity: str, unit: str) -> float:
        """
            Convert quantity of substance to unit.

            Arguments:
                substance: Substance in question.
                quantity: Quantity of substance ('10 mL').
                unit: Unit to convert quantity to ('mol').

            Returns: Converted value.

        """

        if not isinstance(substance, Substance):
            raise TypeError(f"Invalid type for substance, {type(substance)}")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")

        value, quantity_unit = Unit.parse_quantity(quantity)
        return Unit.convert_from(substance, value, quantity_unit, unit)

    @staticmethod
    def convert_to_storage(value: float, unit: str) -> float:
        """

        Converts value to storage format.
        Example: (1, 'L') -> 1e6 uL

        Arguments:
            value: Value to be converted.
            unit: Unit value is in. ('uL', 'mL', 'mol', etc.)

        Returns: Converted value.
        """

        if not isinstance(value, (int, float)):
            raise TypeError("Value must be a float.")
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")

        if unit[-1] == 'L':
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-1])
            result = value * prefix_value / Unit.convert_prefix_to_multiplier(config.volume_storage_unit[:-1])
        else:  # moles
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-3])
            result = value * prefix_value / Unit.convert_prefix_to_multiplier(config.moles_storage_unit[:-3])
        return round(result, config.internal_precision)

    @staticmethod
    def convert_from_storage(value: float, unit: str) -> float:
        """

        Converts value from storage format.
        Example: (1e3 uL, 'mL') -> 1

        Arguments:
            value: Value to be converted.
            unit: Unit value should be in. ('uL', 'mL', 'mol', etc.)

        Returns: Converted value.

        """
        if not isinstance(value, (int, float)):
            raise TypeError("Value must be a float.")
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")

        if unit[-1] == 'L':
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-1])
            result = value * Unit.convert_prefix_to_multiplier(config.volume_storage_unit[0]) / prefix_value
        elif unit[-3:] == 'mol':  # moles
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-3])
            result = value * Unit.convert_prefix_to_multiplier(config.moles_storage_unit[0]) / prefix_value
        else:
            raise ValueError("Invalid unit.")
        return round(result, config.internal_precision)

    @staticmethod
    def convert_from_storage_to_standard_format(substance: Substance, quantity: float) -> Tuple[float, str]:
        """
        Converts a quantity of a substance to a standard format.
        Example: (water, 1e6) -> (18.015, 'mL'), (NaCl, 1e6) -> (58.443, 'g')

        Args:
            substance: Substance
            quantity: Quantity in storage format.

        Returns: Tuple of quantity and unit.

        """
        if isinstance(substance, Substance):
            if substance.is_solid():
                unit = 'g'
                # convert moles to grams
                # molecular weight is in g/mol
                quantity *= Unit.convert_prefix_to_multiplier(config.moles_storage_unit[:-3]) * substance.mol_weight
            elif substance.is_liquid():
                unit = 'L'
                # convert moles to liters
                # molecular weight is in g/mol
                # density is in g/mL
                quantity *= (Unit.convert_prefix_to_multiplier(config.moles_storage_unit[:-3])
                             * substance.mol_weight / substance.density / 1e3)
            else:
                # This shouldn't happen.
                raise TypeError("Invalid subtype for substance.")
        else:
            raise TypeError("Invalid type for substance.")

        multiplier = 1
        while quantity < 1 and multiplier > 1e-6:
            quantity *= 1e3
            multiplier /= 1e3

        unit = {1: '', 1e-3: 'm', 1e-6: 'u'}[multiplier] + unit

        quantity = round(quantity, config.internal_precision)
        return quantity, unit

    @staticmethod
    def get_human_readable_unit(value: float, unit: str) -> Tuple[float, str]:
        """
        Returns a more human-readable value and unit.

        Args:
            value: Value to work with.
            unit:  Unit to determine type and default unit if value is zero.

        Returns: Tuple of new value and unit

        """
        # If the value is zero, return early with the provided unit
        if value == 0:
            return value, unit
        
        # Convert argument 'unit' into the corresponding base unit, and adjust 
        # value by the multiplier corresponding to the provided unit's prefix.
        if unit[-1] == 'L':
            value *= Unit.convert_prefix_to_multiplier(unit[:-1])
            unit = 'L'
        elif unit[-3:] == 'mol':
            value *= Unit.convert_prefix_to_multiplier(unit[:-3])
            unit = 'mol'
        elif unit[-1] == 'g':
            value *= Unit.convert_prefix_to_multiplier(unit[:-1])
            unit = 'g'

        # Determine the 1e3-scale multiplier needed to put 'value' in the range
        # 1 to 1000. This multiplier cannot exceed 1e6 ('M' prefix) and cannot 
        # be lower than 1e-9 ('n' prefix).
        multiplier = 1.0

        # Compute multiplier for values less than one
        while value < 1 and multiplier > 1e-9:
            value *= 1e3
            multiplier /= 1e3

        # Compute multiplier for values greater than 1000
        while value > 1000 and multiplier < 1e6:
            value /= 1e3
            multiplier *= 1e3

        return round(value, config.precisions['default']), \
                Unit.convert_multiplier_to_prefix(multiplier) + unit