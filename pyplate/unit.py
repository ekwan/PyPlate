from typing import Tuple

import math
import re

from pyplate.config import config


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
            prefix: A supported prefix (e.g. an element of Unit.PREFIXES).

        Returns:
            multiplier (float): The multiplier of the corresponding prefix.

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
            multiplier (float): A float whose order of magnitude corresponds to
                                a supported prefix.

        Returns:
            prefix (str): A supported prefix corresponding to the provided 
                          multiplier.

        """
        # Check type of multiplier argument
        if not isinstance(multiplier, (float, int)):
            raise TypeError("Multiplier must be a number.")
        
        # Determine the nearest floored power of ten
        #   E.g. 2500 -> 1000,  or  0.000724 -> 1e-4
        try: 
            multiplier = 10 ** math.floor(math.log10(abs(multiplier)))
        except (ValueError, OverflowError) as e:
            raise ValueError(f"Invalid multiplier: {multiplier}")

        if multiplier in Unit._PREFIX_LOOKUP:
            return Unit._PREFIX_LOOKUP[multiplier]
        raise ValueError(f"Invalid multiplier: {multiplier}")

    @staticmethod
    def parse_prefixed_unit(unit: str) -> Tuple[str, float]:
        """
        Converts a string containing a prefixed unit into its base unit and 
        the prefix's multiplier. A `ValueError` will be raised for unsupported 
        units.

        Args:
            unit (str): The prefixed unit to be parsed (base units without a
                        prefix will also be parsed correctly).
        Returns:
            base_unit (str): The base unit that corresponds to the prefixed unit.
                               E.g. For the unit 'mmol', the base unit is 'mol'.

            multiplier (float): The multiplier for the prefix of the passed 
                                argument.
        """
        # Check to see if the extracted unit is a valid unit.
        for base_unit in Unit.BASE_UNITS_PLUS_CONCENTRATION:
            if unit.endswith(base_unit):
                # Set the prefix to the substring preceding the base unit 
                prefix = unit[:-len(base_unit)]

                # Parse the prefix (will raise a ValueError if it fails)
                # and multiply the value by the associated multiplier
                # (e.g. m -> 1e-3)
                try:
                    multiplier = Unit.convert_prefix_to_multiplier(prefix)
                except ValueError as e:
                    raise ValueError(f"Invalid unit '{unit}'") from e
                
                return base_unit, multiplier
            
        # If no base units matched the end of the unit string, the unit must
        # be invalid. Raise a ValueError stating as much.
        raise ValueError(f"Invalid unit '{unit}'.")
            
    @staticmethod
    def parse_quantity(quantity: str) -> Tuple[float, str]:
        """
        Splits a quantity into a value and unit, converting any SI prefix.
        
        Example: '10 mL' -> (0.01, 'L')

        Arguments:
            quantity (str): The quantity to convert.

        Returns: 
            value (float): The magnitude of the quantity in terms of the 
                            base unit.
            base_unit (str): The base unit of the quantity 
                               E.g. for the quantity '1 mL' the base unit is 'L' 

        """
        
        # Ensure that the quantity is a string
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")

        # Match the primary regular expression against the quantity string
        match = Unit._PRIMARY_QUANTITY_PATTERN_COMPILED.match(quantity)

        # If matching fails, try to match with the secondary regular expression
        if not match:
            match = Unit._SECONDARY_QUANTITY_PATTERN_COMPILED.match(quantity)

            # If matching fails again, fail to parse the quantity and raise a ValueError
            if not match:
                raise ValueError(f"Could not parse '{quantity}'.")
            
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
        try:
            base_unit, multiplier = Unit.parse_prefixed_unit(unit)
        except ValueError as e:
            raise e
        
        # Compute the value converted into the parsed base unit and return the 
        # value-unit pair.
        return value * multiplier, base_unit

    @staticmethod
    def parse_concentration(concentration : str) -> Tuple[float, str, str]:
        """
        Parses concentration string to a tuple triplet of the form (value, 
        numerator, denominator).

        Args:
            concentration (str): The concentration to be parsed.
                                    E.g. '1 M', '1 umol/uL', '0.1 umol/10 uL'

        Returns: 
            value (float): The magnitude of the concentration in terms of the
                            parsed base units in the numerator and denominator.
            numerator (str): The base unit of the numerator.
            denominator (str): The base unit of the denominator.
        """
        if not isinstance(concentration, str):
            raise TypeError("Concentration must be str.")        

        # Define the parsing error string
        parse_error_msg = f"Could not parse '{concentration}'."

        # Strip whitespace for pre-processing steps
        concentration = concentration.strip()

        # If supported concentration units are provided (e.g. 'M' or 'm'), parse
        # them into the equivalent 'numerator unit/denomintor unit' format so 
        # that the rest of the function handles them properly. If the unit 
        # provided is not supported, raise an error. 
        if '/' not in concentration:
            if concentration[-1] == 'm':
                concentration = concentration[:-1] + 'mol/kg'
            elif concentration[-1] == 'M':
                concentration = concentration[:-1] + 'mol/L'
            else:
                raise ValueError(parse_error_msg + " Unsupported concentration "
                                 "unit. Only m and M are allowed as "
                                 "concentration units.")
        
        # Define the value which will eventually be returned (this will be 
        # conditionally modified by various parsing steps below).
        value = 1

        # Define the supported weight percentage and volume percentage 
        # concentration formats and their 'numerator unit/denominator unit' 
        # equivalents.
        replacements = {'%v/v': 'L/L', '%w/w': 'g/g', 
                        '%w/v': config.default_weight_volume_units}
        
        # If a weight percentage or volume percentage concentration was provided,
        # perform the substitution specified by the above dictionary, and reduce
        # the value by a factor of 1/100.
        if concentration[-4:] in replacements:
            concentration = concentration[:-4] + replacements[concentration[-4:]]
            value *= 0.01

        # Parse the concentration string into a numerator and denominator. 
        split_by_slash_results = concentration.split('/')
        if len(split_by_slash_results) != 2:
            raise ValueError(parse_error_msg + 
                             " No more than one '/' should be used.")
        numerator, denominator = split_by_slash_results

        # Try to parse the numerator into a valid quantity
        try:
            numerator_value, numerator_unit = Unit.parse_quantity(numerator)
        except ValueError as e:
            raise ValueError(parse_error_msg + " Invalid numerator.")
        
        # Molarity is currently supported in Unit.parse_quantity(), but it 
        # cannot be allowed in the numerator of the concentration.
        if numerator_unit == 'M':
            raise ValueError(parse_error_msg + " Invalid numerator.")
        
        # Try to parse the denominator into a valid quantity OR a valid unit
        #
        # NOTE: It is quite difficult to distinguish between a user incorrectly
        # specifying a denominator unit and incorrectly specifying a denominator
        # quantity, especially since requirement for spaces in quantities is no
        # longer required. Thus, the raised error does not distinguish between 
        # these two cases.
        denominator = denominator.strip()
        try:
            denom_unit, denom_value = Unit.parse_prefixed_unit(denominator)
        except ValueError:
            try:
                denom_value, denom_unit = Unit.parse_quantity(denominator)
            except ValueError:
                raise ValueError(parse_error_msg + " Invalid denominator.")

        # Molarity is currently supported in Unit.parse_quantity(), but it 
        # cannot be allowed in the denominator of the concentration.
        if denom_unit == 'M':
            raise ValueError(parse_error_msg + " Invalid denominator.")

        # Multiply the existing value by the parsed numerator and denominator 
        # scale factors
        try:
            value *= numerator_value / denom_value
        except ZeroDivisionError:
            raise ValueError(parse_error_msg + " Denominator quantity cannot "
                             "be zero.")

        if math.isnan(value):
            raise ValueError(parse_error_msg + " Resulting concentration was "
                             "NaN.")

        return round(value, config.internal_precision), \
                    numerator_unit, denom_unit

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
    def convert_from_storage_to_standard_format(substance, quantity: float) -> Tuple[float, str]:
        """
        Converts a quantity of a substance to a standard format.
        Example: (water, 1e6) -> (18.015, 'mL'), (NaCl, 1e6) -> (58.443, 'g')

        Args:
            substance: Substance
            quantity: Quantity in storage format.

        Returns: Tuple of quantity and unit.

        """
        from pyplate.substance import Substance
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