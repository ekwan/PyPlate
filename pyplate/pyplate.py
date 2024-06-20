"""

pyplate: a tool for designing chemistry experiments in plate format

Substance: An abstract chemical or biological entity (e.g., reagent, enzyme, solvent, etc.).
           Immutable. Solids and enzymes are assumed to require zero volume.

Container: Stores specified quantities of Substances in a vessel with a given maximum volume. Immutable.

Plate: A spatially ordered collection of Containers, like a 96 well plate.
       The spatial arrangement must be rectangular. Immutable.

Recipe: A list of instructions for transforming one set of containers into another.

Storage format is defined in pyplate.yaml for volumes and moles.

    Example:
        # 1e-6 means we will store volumes as microliters
        volume_storage: 'uL'

        # 1e-6 means we will store moles as micromoles.
        moles_storage: 'umol'

All classes in this package are friends and use private methods of other classes freely.

All internal computations are rounded to config.internal_precision to maintain sanity.
    Rounding errors quickly compound.
All values returned to the user are rounded to config.precisions for ease of use.
"""

# Allow typing reference while still building classes
from __future__ import annotations

from functools import cache
from typing import Tuple, Dict, Iterable
from copy import deepcopy, copy
import numpy
import numpy as np
import pandas
from tabulate import tabulate

from pyplate.slicer import Slicer
from . import Config

config = Config()


class Unit:
    """
    Provides unit conversion utility functions.
    """

    @staticmethod
    def convert_prefix_to_multiplier(prefix: str) -> float:
        """

        Converts an SI prefix into a multiplier.
        Example: "m" -> 1e-3, "u" -> 1e-6

        Arguments:
            prefix:

        Returns:
             Multiplier (float)

        """
        if not isinstance(prefix, str):
            raise TypeError("SI prefix must be a string.")
        prefixes = {'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3, 'c': 1e-2, 'd': 1e-1, '': 1, 'da': 1e1, 'k': 1e3,
                    'M': 1e6}
        if prefix in prefixes:
            return prefixes[prefix]
        raise ValueError(f"Invalid prefix: {prefix}")

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
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a string.")

        if quantity.count(' ') != 1:
            raise ValueError("Value and unit must be separated by a single space.")

        value, unit = quantity.split(' ')
        try:
            value = float(value)
        except ValueError as exc:
            raise ValueError("Value is not a valid float.") from exc

        if unit == 'U':
            return value, unit
        for base_unit in ['mol', 'g', 'L', 'M']:
            if unit.endswith(base_unit):
                prefix = unit[:-len(base_unit)]
                value = value * Unit.convert_prefix_to_multiplier(prefix)
                return value, base_unit
        raise ValueError("Invalid unit {base_unit}.")

    @staticmethod
    def parse_concentration(concentration) -> Tuple[float, str, str]:
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
        units = ('mol', 'L', 'g', 'U')
        for unit in units:
            if numerator[1].endswith(unit):
                numerator[0] *= Unit.convert_prefix_to_multiplier(numerator[1][:-len(unit)])
                numerator[1] = unit
            if denominator[0].endswith(unit):
                numerator[0] /= Unit.convert_prefix_to_multiplier(denominator[0][:-len(unit)])
                denominator[0] = unit
        if numerator[1] not in ('U', 'mol', 'L', 'g') or denominator[0] not in ('U', 'mol', 'L', 'g'):
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

        for suffix in ['U', 'L', 'g', 'mol']:
            if from_unit.endswith(suffix):
                prefix = from_unit[:-len(suffix)]
                quantity *= Unit.convert_prefix_to_multiplier(prefix)
                from_unit = suffix
                break
        else:  # suffix not found
            raise ValueError(f"Invalid unit {from_unit}")

        if from_unit == 'U' and not substance.is_enzyme():
            raise ValueError("Only enzymes can be measured in activity units.")

        for suffix in ['U', 'L', 'g', 'mol']:
            if to_unit.endswith(suffix):
                prefix = to_unit[:-len(suffix)]
                to_unit = suffix
                break
        else:  # suffix not found
            raise ValueError(f"Invalid unit {to_unit}")

        result = None

        if to_unit == 'U':
            if not substance.is_enzyme():
                return 0
            elif from_unit == 'mol':
                return 0
            elif from_unit == 'L':
                # L * (1000 mL/L) * (U/mL)
                result = quantity * 1000. * substance.density
            elif from_unit == 'g':
                # g * (U/g)
                result = quantity * substance.specific_activity
            elif from_unit == 'U':
                result = quantity
        elif to_unit == 'L':
            if from_unit == 'L':
                result = quantity
            elif from_unit == 'mol':
                if substance.is_enzyme():
                    return 0
                # mol * g/mol / (g/mL)
                result_in_mL = quantity * substance.mol_weight / substance.density
                result = result_in_mL / 1000.
            elif from_unit == 'g':
                if substance.is_enzyme():
                    # g * (U/g) / (U/mL) * (1 L / 1000 mL)
                    result = quantity * substance.specific_activity / substance.density / 1000.
                else:
                    # g / (g/mL)
                    result_in_mL = quantity / substance.density
                    result = result_in_mL / 1000
            elif from_unit == 'U':
                if not substance.is_enzyme():
                    return 0
                # U / (U/mL) * (1 L / 1000 mL)
                result = quantity / substance.density / 1000.
        elif to_unit == 'mol':
            if substance.is_enzyme():
                return 0
            if from_unit == 'U':
                return 0
            elif from_unit == 'L':
                value_in_mL = quantity * 1000.  # L * mL/L
                # mL * g/mL / (g/mol)
                result = value_in_mL * substance.density / substance.mol_weight
            elif from_unit == 'mol':
                result = quantity
            elif from_unit == 'g':
                # g / (g/mol)
                result = quantity / substance.mol_weight
        elif to_unit == 'g':
            if from_unit == 'U':
                if not substance.is_enzyme():
                    return 0
                # U / (U/g)
                result = quantity / substance.specific_activity
            elif from_unit == 'L':
                if substance.is_enzyme():
                    # L * (1000 mL/L) * (U/mL) / (U/g)
                    result = quantity * 1000. * substance.density / substance.specific_activity
                else:
                    # L * (1000 mL/L) * g/mL
                    result = quantity * 1000. * substance.density
            elif from_unit == 'mol':
                if substance.is_enzyme():
                    return 0
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
    def convert_from_storage_to_standard_format(what: Substance | Container, quantity: float) -> Tuple[float, str]:
        """
        Converts a quantity of a substance or container to a standard format.
        Example: (water, 1e6) -> (18.015, 'mL'), (NaCl, 1e6) -> (58.443, 'g'), (Amylase, 1) -> (1, 'U')

        Args:
            what: Substance or Container
            quantity: Quantity in storage format.

        Returns: Tuple of quantity and unit.

        """
        if isinstance(what, Substance):
            if what.is_enzyme():
                unit = 'U'
            elif what.is_solid():
                unit = 'g'
                # convert moles to grams
                # molecular weight is in g/mol
                quantity *= Unit.convert_prefix_to_multiplier(config.moles_storage_unit[:-3]) * what.mol_weight
            elif what.is_liquid():
                unit = 'L'
                # convert moles to liters
                # molecular weight is in g/mol
                # density is in g/mL
                quantity *= (Unit.convert_prefix_to_multiplier(config.moles_storage_unit[:-3])
                             * what.mol_weight / what.density / 1e3)
            else:
                # This shouldn't happen.
                raise TypeError("Invalid type for what.")
        elif isinstance(what, Container):
            # Assume the container contains a liquid
            unit = 'L'
            quantity *= Unit.convert_prefix_to_multiplier(config.volume_storage_unit[:-1])
        else:
            raise TypeError("Invalid type for what.")

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
        if value == 0:
            return value, unit
        value = abs(value)
        if unit[-1] == 'L':
            unit = 'L'
        elif unit[-3:] == 'mol':
            unit = 'mol'
        elif unit[-1] == 'g':
            unit = 'g'
        elif unit[-1] == 'U':
            unit = 'U'
        multiplier = 1.0
        while value < 1:
            value *= 1e3
            multiplier /= 1e3

        multiplier = max(multiplier, 1e-6)

        return value, {1: '', 1e-3: 'm', 1e-6: 'u'}[multiplier] + unit

    @staticmethod
    def calculate_concentration_ratio(solute: Substance, concentration: str, solvent: Substance) \
            -> Tuple[float, str, str]:
        # TODO: eliminate this from dilute and tests.
        """
        Helper function for dealing with concentrations.

        Returns: ratio of moles or Activity Units per mole storage unit ('umol', etc.).

        """
        # Formulas used here are found in solution_formulas.rst
        c, numerator, denominator = Unit.parse_concentration(concentration)
        if numerator not in ('g', 'L', 'mol', 'U'):
            raise ValueError("Invalid unit in numerator.")
        if denominator not in ('g', 'L', 'mol'):
            raise ValueError("Invalid unit in denominator.")

        ratio = None  # ration of solute to solvent in moles
        if numerator == 'g':
            if denominator == 'g':
                ratio = c * solvent.mol_weight / (1 - c) / solute.mol_weight
            elif denominator == 'mol':
                ratio = c / (solute.mol_weight - c)
            elif denominator == 'L':
                c /= 1000  # g/mL
                ratio = c * solvent.mol_weight / (solute.mol_weight * solvent.density * (1 - c / solute.density))
        elif numerator == 'L':
            if denominator == 'g':
                c *= 1000  # mL/g
                ratio = c * solvent.mol_weight / (solute.mol_weight * (1 / solute.density - c))
            elif denominator == 'mol':
                c *= 1000  # mL/mol
                ratio = c / (solute.mol_weight / solute.density - c)
            elif denominator == 'L':
                ratio = c * solvent.mol_weight / solvent.density / (solute.mol_weight / solute.density) / (1 - c)
        elif numerator == 'mol':
            if denominator == 'g':
                ratio = c * solvent.mol_weight / (1 - c * solute.mol_weight)
            elif denominator == 'mol':
                ratio = c / (1 - c)
            elif denominator == 'L':
                c /= 1000  # mol/mL
                ratio = c * solvent.mol_weight / solvent.density / (1 - c * solute.mol_weight / solute.density)
        elif numerator == 'U':
            if denominator == 'g':
                ratio = c * solvent.mol_weight
            elif denominator == 'L':
                # density is g/mL
                ratio = c * solvent.mol_weight / solvent.density / 1000.0
            else:
                ratio = c
            # ratio can be multiplied by a stored value of moles to get number of U
            ratio *= Unit.convert_from_storage(1, 'mol')
        return ratio, numerator, denominator


class Substance:
    """
    An abstract chemical or biological entity (e.g., reagent, enzyme, solvent, etc.). Immutable.
    Enzymes are assumed to require zero volume.

    Attributes:
        name: Name of substance.
        mol_weight: Molecular weight (g/mol).
        specific_activity: Activity units per mass if `Substance` is an enzyme (U/g).
        density: Density if `Substance` is a liquid (g/mL).
        concentration: Calculated concentration if `Substance` is a liquid (mol/mL).
        molecule: `cctk.Molecule` if provided.
    """

    SOLID = 1
    LIQUID = 2
    ENZYME = 3

    classes = {SOLID: 'Solids', LIQUID: 'Liquids', ENZYME: 'Enzymes'}

    def __init__(self, name: str, mol_type: int, molecule=None):
        """
        Create a new substance.

        Arguments:
            name: Name of substance.
            mol_type: Substance.LIQUID, Substance.SOLID, or Substance.ENZYME.
            molecule: (optional) A cctk.Molecule.

        If  cctk.Molecule is provided, molecular weight will automatically populate.
        Note: Support for isotopologues will be added in the future.

        """
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        if not isinstance(mol_type, int):
            raise TypeError("Type must be an int.")
        if len(name) == 0:
            raise ValueError("Name must not be empty.")

        self.name = name
        self._type = mol_type
        self.specific_activity = None  # U/g
        self.mol_weight = self.concentration = None
        self.density = float('inf')
        self.molecule = molecule

    def __repr__(self):
        return f"{self.name} ({'SOLID' if self.is_solid() else 'LIQUID' if self.is_liquid() else 'ENZYME'})"

    def __eq__(self, other):
        if not isinstance(other, Substance):
            return False
        return self.name == other.name and self._type == other._type and self.mol_weight == other.mol_weight \
            and self.density == other.density and self.concentration == other.concentration

    def __hash__(self):
        return hash((self.name, self._type, self.mol_weight, self.density, self.concentration))

    @staticmethod
    def solid(name: str, mol_weight: float, molecule=None) -> Substance:
        """
        Creates a solid substance.

        Arguments:
            name: Name of substance.
            mol_weight: Molecular weight in g/mol
            molecule: (optional) A cctk.Molecule

        Returns: New substance.

        """
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        if not isinstance(mol_weight, (int, float)):
            raise TypeError("Molecular weight must be a float.")

        if not mol_weight > 0:
            raise ValueError("Molecular weight must be positive.")

        substance = Substance(name, Substance.SOLID, molecule)
        substance.mol_weight = mol_weight
        substance.density = config.default_solid_density
        return substance

    @staticmethod
    def liquid(name: str, mol_weight: float, density: float, molecule=None) -> Substance:
        """
        Creates a liquid substance.

        Arguments:
            name: Name of substance.
            mol_weight: Molecular weight in g/mol
            density: Density in g/mL
            molecule: (optional) A cctk.Molecule

        Returns: New substance.

        """
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        if not isinstance(mol_weight, (int, float)):
            raise TypeError("Molecular weight must be a float.")
        if not isinstance(density, (int, float)):
            raise TypeError("Density must be a float.")

        if not mol_weight > 0:
            raise ValueError("Molecular weight must be positive.")
        if not density > 0:
            raise ValueError("Density must be positive.")

        substance = Substance(name, Substance.LIQUID, molecule)
        substance.mol_weight = mol_weight  # g / mol
        substance.density = density  # g / mL
        substance.concentration = density / mol_weight  # mol / mL
        return substance

    @staticmethod
    def enzyme(name: str, specific_activity: str, molecule=None) -> Substance:
        """
        Creates an enzyme.

        Arguments:
            name: Name of enzyme.
            specific_activity: A ratio of activity units to mass ('10 U/g', '10 U/mg', '0.1 mg/U')
            molecule: (optional) A cctk.Molecule

        Returns: New substance.

        """
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")

        if not isinstance(specific_activity, str):
            raise TypeError("Specific activity must be a str.")

        try:
            value, numerator, denominator = Unit.parse_concentration(specific_activity)
        except Exception:
            raise ValueError("Specific activity must be in U/g or g/U.")

        if value < 0:
            raise ValueError("Specific activity must be positive.")

        substance = Substance(name, Substance.ENZYME, molecule)
        substance.density = config.default_enzyme_density
        value, numerator, denominator = Unit.parse_concentration(specific_activity)

        if numerator == 'U' and denominator == 'g':
            substance.specific_activity = value
        elif numerator == 'g' and denominator == 'U':
            substance.specific_activity = 1 / value
        else:
            raise ValueError("Specific activity must be in U/g or g/U.")

        return substance

    def is_solid(self) -> bool:
        """
        Return true if `Substance` is a solid.
        """
        return self._type == Substance.SOLID

    def is_liquid(self) -> bool:
        """
        Return true if `Substance` is a liquid.
        """
        return self._type == Substance.LIQUID

    def is_enzyme(self) -> bool:
        """
        Return true if `Substance` is an enzyme.
        """
        return self._type == Substance.ENZYME


class Container:
    """
    Stores specified quantities of Substances in a vessel with a given maximum volume. Immutable.

    Attributes:
        name: Name of the Container.
        contents: A dictionary of Substances to floats denoting how much of each Substance is the Container.
        volume: Current volume held in the Container in storage format.
        max_volume: Maximum volume Container can hold in storage format.
    """

    def __init__(self, name: str, max_volume: str = 'inf L',
                 initial_contents: Iterable[Tuple[Substance, str]] = None):
        """
        Create a Container.

        Arguments:
            name: Name of container
            max_volume: Maximum volume that can be stored in the container in mL
            initial_contents: (optional) Iterable of tuples of the form (Substance, quantity)
        """
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        if len(name) == 0:
            raise ValueError("Name must not be empty.")

        if not isinstance(max_volume, str):
            raise TypeError("Maximum volume must be a str, ('10 mL').")
        max_volume, _ = Unit.parse_quantity(max_volume)
        if max_volume <= 0:
            raise ValueError("Maximum volume must be positive.")
        self.name = name
        self.contents: Dict[Substance, float] = {}
        self.volume = 0.0
        self.max_volume = Unit.convert_to_storage(max_volume, 'L')
        self.experimental_conditions = {}
        if initial_contents:
            if not isinstance(initial_contents, Iterable):
                raise TypeError("Initial contents must be iterable.")
            for entry in initial_contents:
                if not isinstance(entry, Iterable) or not len(entry) == 2:
                    raise TypeError("Element in initial_contents must be a (Substance, str) tuple.")
                substance, quantity = entry
                if not isinstance(substance, Substance) or not isinstance(quantity, str):
                    raise TypeError("Element in initial_contents must be a (Substance, str) tuple.")
                self._self_add(substance, quantity)
            contents = []
            for substance, quantity in self.contents.items():
                quantity, unit = Unit.convert_from_storage_to_standard_format(substance, quantity)
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                contents.append(f"{round(quantity, precision)} {unit} of {substance.name}")
            self.instructions = f"Add {', '.join(contents)}"
            if self.max_volume != float('inf'):
                max_volume, unit = Unit.convert_from_storage_to_standard_format(self, self.max_volume)
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                self.instructions += f" to a {round(max_volume, precision)} {unit} container."
            else:
                self.instructions += " to a container."
        else:
            if self.max_volume != float('inf'):
                max_volume, unit = Unit.convert_from_storage_to_standard_format(self, self.max_volume)
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                self.instructions = f"Create a {round(max_volume, precision)} {unit} container."
            else:
                self.instructions = "Create a container."

    def __eq__(self, other):
        if not isinstance(other, Container):
            return False
        return self.name == other.name and self.contents == other.contents and \
            self.volume == other.volume and self.max_volume == other.max_volume

    def __hash__(self):
        return hash((self.name, self.volume, self.max_volume, *tuple(map(tuple, self.contents.items()))))

    def _self_add(self, source: Substance, quantity: str) -> None:
        """

        Adds `Substance` to current `Container`, mutating it.
        Only to be used in the constructor and immediately after copy.

        Arguments:
            source: Substance to add.
            quantity: How much to add. ('10 mol')

        """
        if not isinstance(source, Substance):
            raise TypeError("Source must be a Substance.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")

        volume_to_add = Unit.convert(source, quantity, config.volume_storage_unit)
        if source.is_enzyme():
            amount_to_add = Unit.convert(source, quantity, 'U')
        else:
            amount_to_add = Unit.convert(source, quantity, config.moles_storage_unit)
        if self.volume + volume_to_add > self.max_volume:
            raise ValueError("Exceeded maximum volume")
        self.volume = round(self.volume + volume_to_add, config.internal_precision)
        self.contents[source] = round(self.contents.get(source, 0) + amount_to_add, config.internal_precision)

    def _transfer(self, source_container: Container, quantity: str) -> Tuple[Container, Container]:
        """
        Move quantity ('10 mL', '5 mg') from container to self.

        Arguments:
            source_container: `Container` to transfer from.
            quantity: How much to transfer.

        Returns: New source and destination container.
        """

        if not isinstance(source_container, Container):
            raise TypeError("Invalid source type.")
        quantity_to_transfer, unit = Unit.parse_quantity(quantity)

        if unit == 'L':
            volume_to_transfer = Unit.convert_to_storage(quantity_to_transfer, 'L')
            volume_to_transfer = round(volume_to_transfer, config.internal_precision)

            if volume_to_transfer > source_container.volume:
                raise ValueError(f"Not enough mixture left in source container ({source_container.name}). " +
                                 f"Only {Unit.convert_from_storage(source_container.volume, 'mL')} mL available, " +
                                 f"{Unit.convert_from_storage(volume_to_transfer, 'mL')} mL needed.")
            ratio = volume_to_transfer / source_container.volume

        elif unit == 'g':
            mass_to_transfer = round(quantity_to_transfer, config.internal_precision)
            total_mass = 0
            for substance, amount in source_container.contents.items():
                source_unit = 'U' if substance.is_enzyme() else config.moles_storage_unit
                total_mass += Unit.convert_from(substance, amount, source_unit, "g")
            ratio = mass_to_transfer / total_mass
        elif unit == 'mol':
            moles_to_transfer = Unit.convert_to_storage(quantity_to_transfer, 'mol')
            total_moles = sum(amount for substance, amount in source_container.contents.items()
                              if not substance.is_enzyme())
            ratio = moles_to_transfer / total_moles
        elif unit == 'U':
            total_activity = sum(amount for substance, amount in source_container.contents.items()
                                 if substance.is_enzyme())
            if total_activity == 0:
                raise ValueError("There are no enzymes in the source container.")
            ratio = quantity_to_transfer / total_activity
        else:
            raise ValueError("Invalid quantity unit.")

        source_container, to = deepcopy(source_container), deepcopy(self)
        for substance, amount in source_container.contents.items():
            to_transfer = amount * ratio
            to.contents[substance] = round(to.contents.get(substance, 0) + to_transfer,
                                           config.internal_precision)
            source_container.contents[substance] = round(source_container.contents[substance] - to_transfer,
                                                         config.internal_precision)
            # if quantity to remove is the same as the current amount plus a very small delta,
            # we will get a negative 0 answer.
            if source_container.contents[substance] == -0.0:
                source_container.contents[substance] = 0.0
        if source_container.has_liquid():
            transfer = Unit.convert_from_storage(ratio * source_container.volume, 'L')
            transfer, unit = Unit.get_human_readable_unit(transfer, 'L')
        else:
            # total mass in source container times ratio
            mass = sum(Unit.convert(substance,
                                    f"{amount} {config.moles_storage_unit if not substance.is_enzyme() else 'U'}",
                                    "mg") for substance, amount in source_container.contents.items())
            transfer, unit = Unit.get_human_readable_unit(mass * ratio, 'mg')
        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        to.instructions += f"\nTransfer {round(transfer, precision)} {unit} of {source_container.name} to {to.name}"
        to.volume = 0
        for substance, amount in to.contents.items():
            unit = 'U' if substance.is_enzyme() else config.moles_storage_unit
            to.volume += Unit.convert(substance, f"{amount} {unit}", config.volume_storage_unit)
        to.volume = round(to.volume, config.internal_precision)
        if to.volume > to.max_volume:
            raise ValueError(f"Exceeded maximum volume in {to.name}.")
        source_container.volume = 0
        for substance, amount in source_container.contents.items():
            unit = 'U' if substance.is_enzyme() else config.moles_storage_unit
            source_container.volume += Unit.convert(substance, f"{amount} {unit}", config.volume_storage_unit)
        source_container.volume = round(source_container.volume, config.internal_precision)

        return source_container, to

    def _transfer_slice(self, source_slice: Plate | PlateSlicer, quantity: str) -> Tuple[Plate, Container]:
        """
        Move quantity ('10 mL', '5 mg') from each well in a slice to self.

        Arguments:
            source_slice: Slice or Plate to transfer from.
            quantity: How much to transfer.

        Returns:
            A new plate and a new container, both modified.
        """

        def helper_func(elem):
            """ Moves volume from elem to to_array[0]"""
            elem, to_array[0] = Container.transfer(elem, to_array[0], quantity)
            return elem

        if isinstance(source_slice, Plate):
            source_slice = source_slice[:]
        if not isinstance(source_slice, PlateSlicer):
            raise TypeError("Invalid source type.")
        to = deepcopy(self)
        source_slice = copy(source_slice)
        source_slice.plate = deepcopy(source_slice.plate)

        to_array = [to]
        source_slice.apply(helper_func)
        to = to_array[0]
        return source_slice.plate, to

    @cache
    def dataframe(self) -> pandas.DataFrame:
        df = pandas.DataFrame(columns=['Volume', 'Mass', 'Moles', 'U'])
        if self.max_volume == float('inf'):
            df.loc['Maximum Volume'] = ['∞', '-', '-', '-']
        else:
            volume, unit = Unit.convert_from_storage_to_standard_format(self, self.max_volume)
            volume = round(volume,
                           config.precisions[unit] if unit in config.precisions else config.precisions['default'])
            df.loc['Maximum Volume'] = [volume, '-', '-', '-']
        totals = {'L': 0, 'g': 0, 'mol': 0, 'U': 0}
        for substance, value in self.contents.items():
            columns = []
            for unit in ['L', 'g', 'mol', 'U']:
                if unit == 'mol' and substance.is_enzyme():
                    columns.append('-')
                elif unit == 'U' and not substance.is_enzyme():
                    columns.append('-')
                else:
                    from_unit = config.moles_storage_unit if not substance.is_enzyme() else 'U'
                    converted_value = Unit.convert_from(substance, value, from_unit, unit)
                    totals[unit] += converted_value
                    converted_value, unit = Unit.get_human_readable_unit(converted_value, unit)
                    precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                    columns.append(f"{round(converted_value, precision)} {unit}")
            df.loc[substance.name] = columns
        columns = []
        for unit in ['L', 'g', 'mol', 'U']:
            value = totals[unit]
            value, unit = Unit.get_human_readable_unit(value, unit)
            precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
            columns.append(f"{round(value, precision)} {unit}")
        df.loc['Total'] = columns

        df.columns.name = self.name
        return df

    @cache
    def _repr_html_(self):
        return self.dataframe().to_html(notebook=True)

    @cache
    def __repr__(self):
        df = self.dataframe()
        return tabulate(df, headers=[self.name] + list(df.columns), tablefmt='pretty')

    @cache
    def has_liquid(self) -> bool:
        """
        Returns: True if any substance in the container is a liquid.
        """
        return any(substance.is_liquid() for substance in self.contents)

    @cache
    def get_substances(self):
        """

        Returns: A set of substances present in the container.

        """
        return set(self.contents.keys())

    def _add(self, source: Substance, quantity: str) -> Container:
        """
        Add the given quantity ('10 mol') of the source substance to the container.

        Arguments:
            source: Substance to add to `destination`.
            quantity: How much `Substance` to add.

        Returns:
            A new container with added substance.
        """
        destination = deepcopy(self)
        destination._self_add(source, quantity)
        return destination

    @staticmethod
    def transfer(source: Container | Plate | PlateSlicer, destination: Container, quantity: str) \
            -> Tuple[Container | Plate | PlateSlicer, Container]:
        """
        Move quantity ('10 mL', '5 mg') from source to destination container,
        returning copies of the objects with amounts adjusted accordingly.

        Arguments:
            source: Container, plate, or slice to transfer from.
            destination: Container to transfer to:
            quantity: How much to transfer.

        Returns:
            A tuple of (T, Container) where T is the type of the source.
        """
        if not isinstance(destination, Container):
            raise TypeError("You can only use Container.transfer into a Container")
        if isinstance(source, Container):
            return destination._transfer(source, quantity)
        if isinstance(source, (Plate, PlateSlicer)):
            return destination._transfer_slice(source, quantity)
        raise TypeError("Invalid source type.")

    def get_concentration(self, solute: Substance, units: str = 'M') -> float:
        """
        Get the concentration of solute in the current solution.

        Args:
            solute: Substance interested in.
            units: Units to return concentration in, defaults to Molar.

        Returns: Concentration

        """
        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(units, str):
            raise TypeError("Units must be a str.")

        mult, *units = Unit.parse_concentration('1 ' + units)

        if solute.is_enzyme():
            numerator = Unit.convert_from(solute, self.contents.get(solute, 0), 'U', units[0])
        else:
            numerator = Unit.convert_from(solute, self.contents.get(solute, 0), config.moles_storage_unit, units[0])

        if numerator == 0:
            return 0

        if units[1].endswith('L'):
            denominator = self.get_volume(units[1])
        else:
            denominator = 0
            for substance, amount in self.contents.items():
                if substance.is_enzyme():
                    denominator += Unit.convert_from(substance, amount, 'U', units[1])
                else:
                    denominator += Unit.convert_from(substance, amount, config.moles_storage_unit, units[1])

        return round(numerator / denominator / mult, config.internal_precision)

    def get_volume(self, unit: str = None) -> float:
        """
        Get the volume of the container.

        Args:
            unit: Unit to return volume in. Defaults to volume_display_unit from config.

        Returns: Volume of the container.

        """
        if unit is None:
            unit = config.volume_display_unit

        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")

        return Unit.convert_from_storage(self.volume, unit)

    @staticmethod
    def create_solution(solute: Substance | Iterable[Substance], solvent: Substance | Container,
                        name: str = None, **kwargs) -> Container:
        """
        Create a solution.

        Two out of concentration, quantity, and total_quantity must be specified.

        Multiple solutes can be, optionally, provided as a list. Each solute will have the desired concentration
        or quantity in the final solution.

        If one value is specified for concentration or quantity and multiple solutes are provided, the value will be
        used for all solutes.

        Arguments:
            solute: What to dissolve. Can be a single Substance or a list of Substances.
            solvent: What to dissolve with. Can be a Substance or a Container.
            name: Optional name for new container.
            concentration: Desired concentration(s). ('1 M', '0.1 umol/10 uL', etc.)
            quantity: Desired quantity of solute(s). ('3 mL', '10 g')
            total_quantity: Desired total quantity. ('3 mL', '10 g')


        Returns:
            New container with desired solution.
        """

        if not isinstance(solvent, (Substance, Container)):
            raise TypeError("Solvent must be a Substance or a Container.")
        if name and not isinstance(name, str):
            raise TypeError("Name must be a str.")

        if isinstance(solute, Substance):
            solute = [solute]
        elif not isinstance(solute, list) or any(not isinstance(substance, Substance) for substance in solute):
            raise TypeError("Solute(s) must be a Substance.")

        concentration = kwargs.get('concentration', None)
        quantity = kwargs.get('quantity', None)
        total_quantity = kwargs.get('total_quantity', None)

        original_solvent = solvent
        if isinstance(solvent, Container):
            # Calculate mol_weight and density of solvent
            # get total mass of solvent
            total_mass = sum(Unit.convert_from(substance, amount, 'U' if substance.is_enzyme() else 'mol', 'g')
                             for substance, amount in solvent.contents.items())
            total_moles = Unit.convert_from_storage(sum(amount for substance, amount in solvent.contents.items()
                                                        if not substance.is_enzyme()), 'mol')
            total_volume = solvent.get_volume('mL')
            if total_moles == 0 or total_volume == 0:
                raise ValueError("Solvent must contain a non-zero amount of substance.")
            # mol_weight = g/mol, density = g/mL
            solvent = Substance.liquid('fake solvent',
                                       mol_weight=total_mass / total_moles, density=total_mass / total_volume)

        if (concentration is not None) + (quantity is not None) + (total_quantity is not None) != 2:
            raise ValueError("Must specify two values out of concentration, quantity, and total quantity.")

        if total_quantity and not isinstance(total_quantity, str):
            raise TypeError("Total quantity must be a str.")

        if not name:
            name = f"Solution of {','.join(substance.name for substance in solute)} in {solvent.name}"

        def convert_one(substance: Substance, u: str) -> float:
            """ Converts 1 mol or U to unit `u` for a given substance. """
            return Unit.convert_from(substance, 1, 'U' if substance.is_enzyme() else 'mol', u)

        # result of linalg.solve will be moles (or 'U') for all solutes solvent

        n = len(solute)
        a = numpy.zeros((n * 2, n + 1), dtype=float)
        b = numpy.zeros(n * 2, dtype=float)
        index = 0
        identity = numpy.identity(n + 1)[0]
        if concentration is not None:
            if isinstance(concentration, str):
                concentration = [concentration] * len(solute)
            elif not isinstance(concentration, Iterable):
                raise TypeError("Concentration(s) must be a str.")
            bottom_arrays = {}
            for i, (c, substance) in enumerate(zip(concentration, solute)):
                if not isinstance(c, str):
                    raise TypeError("Concentration(s) must be a str.")
                try:
                    c, numerator, denominator = Unit.parse_concentration(c)
                except ValueError:
                    raise ValueError(f"Invalid concentration. ({c})")

                if denominator not in bottom_arrays:
                    bottom = numpy.array(list(convert_one(substance, denominator) for substance in solute + [solvent]))
                    bottom_arrays[denominator] = bottom
                else:
                    bottom = bottom_arrays[denominator]

                # c = top/bottom
                a[index] = c * bottom - numpy.roll(identity, i) * convert_one(substance, numerator)
                index += 1

        if quantity is not None:
            if isinstance(quantity, str):
                quantity = [quantity] * len(solute)
            elif not isinstance(quantity, Iterable):
                raise TypeError("Quantity(s) must be a str.")
            for i, (q, substance) in enumerate(zip(quantity, solute)):
                if not isinstance(q, str):
                    raise TypeError("Quantity(s) must be a str.")
                q, unit = Unit.parse_quantity(q)
                a[index] = numpy.roll(identity, i) * convert_one(substance, unit)
                b[index] = q
                index += 1

        if total_quantity is not None:
            total_quantity, total_quantity_unit = Unit.parse_quantity(total_quantity)
            a[index] = numpy.array(
                list(convert_one(substance, total_quantity_unit) for substance in solute + [solvent]))
            b[index] = total_quantity

        xs = numpy.linalg.solve(a[:n + 1], b[:n + 1])
        if any(x <= 0 for x in xs):
            raise ValueError("Solution is impossible to create.")

        for i in range(len(a)):
            if abs(sum(a[i] * xs) - b[i]) > 1e-6:
                raise ValueError("Solution is impossible to create.")

        initial_contents = list((substance, f"{x} {'U' if substance.is_enzyme() else 'mol'}") for x, substance in
                                zip(xs, solute + [solvent]))
        if isinstance(original_solvent, Container):
            result = Container(name, initial_contents=initial_contents[:-1])
            contents = []
            for substance, value in result.contents.items():
                value, unit = Unit.convert_from_storage_to_standard_format(substance, value)
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                contents.append(f"{round(value, precision)} {unit} of {substance.name}")
            _, solvent_amount = initial_contents[-1]
            solvent_volume = Unit.convert_from(solvent, xs[-1], 'mol', 'L')
            solvent_volume, volume_unit = Unit.get_human_readable_unit(solvent_volume, 'L')
            solvent_volume = round(solvent_volume,
                                   config.precisions[volume_unit] if volume_unit in config.precisions else
                                   config.precisions['default'])

            original_solvent, result = Container.transfer(original_solvent, result, solvent_amount)
            result.instructions = ("Add " + ", ".join(contents) +
                                   f" to {solvent_volume} {volume_unit} of {original_solvent.name}.")
            return original_solvent, result
        else:
            result = Container(name, initial_contents=initial_contents)
            contents = []
            for substance, value in result.contents.items():
                value, unit = Unit.convert_from_storage_to_standard_format(substance, value)
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                contents.append(f"{round(value, precision)} {unit} of {substance.name}")
            result.instructions = "Add " + ", ".join(contents) + " to a container."
            return result

    @staticmethod
    def create_solution_from(source: Container, solute: Substance, concentration: str, solvent: Substance | Container,
                             quantity: str, name=None) -> (Tuple[Container, Container] |
                                                           Tuple[Container, Container, Container]):
        """
        Create a diluted solution from an existing solution or solutions.


        Arguments:
            source: Solution to dilute.
            solute: What to dissolve.
            concentration: Desired concentration. ('1 M', '0.1 umol/10 uL', etc.)
            solvent: What to dissolve with (if it is a Container, it can contain some solute).
            quantity: Desired total quantity. ('3 mL', '10 g')
            name: Optional name for new container.

        Returns:
            Residual from the source container (and possibly the solvent container)
             and a new container with the desired solution.

        Raises:
            ValueError: If the solution is impossible to create.
        """

        if not isinstance(source, Container):
            raise TypeError("Source must be a Container.")
        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(concentration, str):
            raise TypeError("Concentration must be a str.")
        if not isinstance(solvent, (Substance, Container)):
            raise TypeError("Solvent must be a Substance or Container.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")
        if name and not isinstance(name, str):
            raise TypeError("Name must be a str.")

        quantity_value, quantity_unit = Unit.parse_quantity(quantity)
        if quantity_value <= 0:
            raise ValueError("Quantity must be positive.")

        if solute not in source.contents:
            raise ValueError(f"Source container does not contain {solute.name}.")

        if solvent == solute:
            raise ValueError("Solute and solvent must be different.")

        if not name:
            name = f"solution of {solute.name} in {solvent.name}"

        # x is amount of source solution in mL, y is amount of solvent in mL
        mass = sum(Unit.convert_from(substance, value, config.moles_storage_unit, 'g') for substance, value in
                   source.contents.items())
        moles = sum(Unit.convert_from(substance, value, config.moles_storage_unit, 'mol') for substance, value in
                    source.contents.items())
        volume = Unit.convert_from_storage(source.volume, 'mL')
        d_x = mass / volume
        mw_x = mass / moles
        m_x = Unit.convert_from_storage(source.contents.get(solute, 0), 'mol') / (volume / 1000)

        if isinstance(solvent, Container):
            mass = sum(Unit.convert_from(substance, value, config.moles_storage_unit, 'g') for substance, value in
                       solvent.contents.items())
            moles = sum(Unit.convert_from(substance, value, config.moles_storage_unit, 'mol') for substance, value in
                        solvent.contents.items())
            volume = Unit.convert_from_storage(solvent.volume, 'mL')
            d_y = mass / volume
            mw_y = mass / moles
            m_y = Unit.convert_from_storage(solvent.contents.get(solute, 0), 'mol') / (volume / 1000)
        else:
            d_y = solvent.density
            mw_y = solvent.mol_weight
            m_y = 0  # no solute in solvent

        mw_s = solute.mol_weight
        d_s = solute.density

        concentration, numerator, denominator = Unit.parse_concentration(concentration)
        a = numpy.array([[0., 0.], [0., 0.]])
        b = numpy.array([0., 0.])

        if numerator == 'mol':
            top = numpy.array([m_x / 1000., m_y / 1000.])
        elif numerator == 'g':
            top = numpy.array([m_x * mw_s / 1000., m_y * mw_s / 1000.])
        elif numerator == 'L':
            # (mL/1000) * mol/L * g/mol * mL/g = mL / 1000 = L
            top = numpy.array([m_x * mw_s / (d_s * 1e6), m_y * mw_s / (d_s * 1e6)])
        else:
            raise ValueError("Invalid numerator.")
        if denominator == 'mol':
            bottom = numpy.array([d_x / mw_x, d_y / mw_y])
        elif denominator == 'g':
            bottom = numpy.array([d_x, d_y])
        elif denominator == 'L':
            bottom = numpy.array([1 / 1000., 1 / 1000.])
        else:
            raise ValueError("Invalid denominator.")

        # concentration = top / bottom -> concentration * bottom - top = 0
        a[0] = concentration * bottom - top

        quantity_value, quantity_unit = Unit.parse_quantity(quantity)

        if quantity_unit == 'g':
            a[1] = numpy.array([d_x, d_y])
        elif quantity_unit == 'L':
            a[1] = numpy.array([1 / 1000., 1 / 1000.])
        elif quantity_value == 'mol':
            a[1] = numpy.array([d_x / mw_x, d_y / mw_y])

        b[1] = quantity_value
        x, y = numpy.linalg.solve(a, b)
        if x < 0 or y < 0:
            raise ValueError("Solution is impossible to create.")

        if isinstance(solvent, Substance):
            if y:
                new_solution = Container(name, initial_contents=[(solvent, f"{y} mL")])
            else:
                new_solution = Container(name)
            if x:
                source, new_solution = Container.transfer(source, new_solution, f"{x} mL")
        else:
            new_solution = Container(name)
            if x:
                source, new_solution = Container.transfer(source, new_solution, f"{x} mL")
            if y:
                solvent, new_solution = Container.transfer(solvent, new_solution, f"{y} mL")

        precision = config.precisions['mL'] if 'mL' in config.precisions else config.precisions['default']
        new_solution.instructions = f"Add {round(y, precision)} mL of {solvent.name} to" + \
                                    f" {round(x, precision)} mL of {source.name}."

        if isinstance(solvent, Substance):
            return source, new_solution
        else:
            return source, solvent, new_solution

    def remove(self, what: (Substance | int) = Substance.LIQUID) -> Container:
        """
        Removes substances from `Container`

        Arguments:
            what: What to remove. Can be a type of substance or a specific substance. Defaults to LIQUID.

        Returns: New Container with requested substances removed.

        """
        new_container = deepcopy(self)
        new_container.contents = {substance: value for substance, value in self.contents.items()
                                  if what not in (substance._type, substance)}
        new_container.volume = 0
        for substance, value in new_container.contents.items():
            substance_unit = 'U' if substance.is_enzyme() else config.moles_storage_unit
            new_container.volume += Unit.convert_from(substance, value, substance_unit, config.volume_storage_unit)

        new_container.instructions = self.instructions
        classes = {Substance.SOLID: 'solid', Substance.LIQUID: 'liquid', Substance.ENZYME: 'enzyme'}
        if what in classes:
            new_container.instructions += f"Remove all {classes[what]}s."
        else:
            new_container.instructions += f"Remove all {what.name}s."
        return new_container

    def dilute(self, solute: Substance, concentration: str, solvent: Substance, name=None) -> Container:
        """
        Dilutes `solute` in solution to `concentration`.

        Args:
            solute: Substance which is subject to dilution.
            concentration: Desired concentration.
            solvent: What to dilute with.
            name: Optional name for new container.

        Returns: A new container containing a solution with the desired concentration of `solute`.

        """
        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(concentration, str):
            raise TypeError("Concentration must be a str.")
        if not isinstance(solvent, Substance):
            raise TypeError("Solvent must be a substance.")
        if name and not isinstance(name, str):
            raise TypeError("New name must be a str.")
        if solute not in self.contents:
            raise ValueError(f"Container does not contain {solute.name}.")

        new_ratio, numerator, denominator = Unit.calculate_concentration_ratio(solute, concentration, solvent)

        if numerator == 'U':
            if not solute.is_enzyme():
                raise TypeError("Solute must be an enzyme.")

        current_ratio = self.contents[solute] / sum(self.contents[substance] for
                                                    substance in self.contents if not substance.is_enzyme())

        if new_ratio <= 0:
            raise ValueError("Solution is impossible to create.")

        if abs(new_ratio - current_ratio) <= 1e-6:
            return deepcopy(self)

        if new_ratio > current_ratio:
            raise ValueError("Desired concentration is higher than current concentration.")

        current_umoles = Unit.convert_from_storage(self.contents.get(solvent, 0), 'umol')
        required_umoles = Unit.convert_from_storage(self.contents[solute], 'umol') / new_ratio - current_umoles
        new_volume = self.volume + Unit.convert(solvent, f"{required_umoles} umol", config.volume_storage_unit)

        if new_volume > self.max_volume:
            raise ValueError("Dilute solution will not fit in container.")

        if name:
            # Note: this copies the container twice
            destination = deepcopy(self)
            destination.name = name
        else:
            destination = self
        needed_umoles = f"{required_umoles} umol"
        result = destination._add(solvent, needed_umoles)
        needed_volume, unit = Unit.get_human_readable_unit(Unit.convert(solvent, needed_umoles, 'L'), 'L')
        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        result.instructions += f"\nDilute with {round(needed_volume, precision)} {unit} of {solvent.name}."
        return result

    def fill_to(self, solvent: Substance, quantity: str) -> Container:
        """
        Fills container with `solvent` up to `quantity`.

        Args:
            solvent: Substance to use to fill.
            quantity: Desired final quantity in container.

        Returns: New Container with desired final `quantity`

        """
        if not isinstance(solvent, Substance):
            raise TypeError("Solvent must be a Substance.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")

        quantity, quantity_unit = Unit.parse_quantity(quantity)
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        if quantity_unit not in ('L', 'g', 'mol'):
            raise ValueError("We can only fill to mass or volume.")

        current_quantity = sum(Unit.convert(substance, f"{value} {config.moles_storage_unit}", quantity_unit)
                               for substance, value in self.contents.items() if not substance.is_enzyme())

        required_quantity = quantity - current_quantity
        result = self._add(solvent, f"{required_quantity} {quantity_unit}")
        required_volume = Unit.convert(solvent, f"{required_quantity} {quantity_unit}", 'L')
        required_volume, unit = Unit.get_human_readable_unit(required_volume, 'L')
        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        result.instructions += f"\nFill with {round(required_volume, precision)} {unit} of {solvent.name}."
        return result


class Plate:
    """
    A spatially ordered collection of Containers, like a 96 well plate.
    The spatial arrangement must be rectangular. Immutable.
    """

    def __init__(self, name: str, max_volume_per_well: str, make: str = "generic", rows=8, columns=12):
        """
            Creates a generic plate.

            Attributes:
                name: name of plate
                max_volume_per_well: maximum volume of each well. (50 uL)
                make: name of this kind of plate
                rows (int or list): number of rows or list of names of rows
                columns (int or list): number of columns or list of names of columns
        """

        if not isinstance(name, str) or len(name) == 0:
            raise ValueError("invalid plate name")
        self.name = name

        if not isinstance(make, str) or len(make) == 0:
            raise ValueError("invalid plate make")
        self.make = make

        if not isinstance(max_volume_per_well, str):
            raise TypeError("Maximum volume must be a str, ('10 mL').")
        max_volume_per_well, _ = Unit.parse_quantity(max_volume_per_well)

        if isinstance(rows, int):
            if rows < 1:
                raise ValueError("illegal number of rows")
            self.n_rows = rows
            self.row_names = []
            for row_num in range(1, rows + 1):
                result = []
                while row_num > 0:
                    row_num -= 1
                    result.append(chr(ord('A') + row_num % 26))
                    row_num //= 26
                self.row_names.append(''.join(reversed(result)))
        elif isinstance(rows, list):
            if len(rows) == 0:
                raise ValueError("must have at least one row")
            for row in rows:
                if not isinstance(row, str):
                    raise ValueError("row names must be strings")
                if len(row.strip()) == 0:
                    raise ValueError(
                        "zero length strings are not allowed as column labels"
                    )
            if len(rows) != len(set(rows)):
                raise ValueError("duplicate row names found")
            self.n_rows = len(rows)
            self.row_names = rows
        else:
            raise ValueError("rows must be int or list")

        if max_volume_per_well <= 0:
            raise ValueError("max volume per well must be greater than zero")
        self.max_volume_per_well = Unit.convert_to_storage(max_volume_per_well, 'L')

        if isinstance(columns, int):
            if columns < 1:
                raise ValueError("illegal number of columns")
            self.n_columns = columns
            self.column_names = [f"{i + 1}" for i in range(columns)]
        elif isinstance(columns, list):
            if len(columns) == 0:
                raise ValueError("must have at least one column")
            for column in columns:
                if not isinstance(column, str):
                    raise ValueError("column names must be strings")
                if len(column.strip()) == 0:
                    raise ValueError(
                        "zero length strings are not allowed as column labels"
                    )
            if len(columns) != len(set(columns)):
                raise ValueError("duplicate column names found")
            self.n_columns = len(columns)
            self.column_names = columns
        else:
            raise ValueError("columns must be int or list")

        self.wells = numpy.array([[Container(f"well {row},{col}",
                                             max_volume=f"{max_volume_per_well} L")
                                   for col in self.column_names] for row in self.row_names])

    def __getitem__(self, item) -> PlateSlicer:
        return PlateSlicer(self, item)

    def __repr__(self):
        return f"Plate: {self.name}"

    def get_volumes(self, substance: (Substance | Iterable[Substance]) = None, unit: str = None) -> numpy.ndarray:
        """

        Arguments:
            unit: unit to return volumes in.
            substance: (optional) Substance to display volumes of.

        Returns:
            numpy.ndarray of volumes for each well in desired unit.

        """

        # Arguments are type checked in PlateSlicer.volumes
        return self[:].get_volumes(substance=substance, unit=unit)

    def get_substances(self) -> set[Substance]:
        """

        Returns: A set of substances present in the slice.

        """
        return self[:].get_substances()

    def get_moles(self, substance: (Substance | Iterable[Substance]), unit: str = None) -> numpy.ndarray:
        """

        Arguments:
            unit: unit to return moles in. ('mol', 'mmol', 'umol', etc.)
            substance: Substance to display moles of.

        Returns: moles of substance in each well.
        """

        # Arguments are type checked in PlateSlicer.moles
        return self[:].get_moles(substance=substance, unit=unit)

    def dataframe(self, unit: str = None, substance: (str | Substance | Iterable[Substance]) = 'all',
                  cmap: str = None, highlight=False) \
            -> pandas.io.formats.style.Styler:
        """

        Arguments:
            unit: unit to return quantities in.
            substance: (optional) Substance or Substances to display quantity of.
            cmap: Colormap to shade dataframe with.
            highlight: Highlight all wells.

        Returns: Shaded dataframe of quantities in each well.

        """
        # Types are checked in PlateSlicer.dataframe
        if unit is None:
            unit = config.volume_display_unit
        return self[:].dataframe(substance=substance, unit=unit, cmap=cmap, highlight=highlight)

    def get_volume(self, unit: str = 'uL') -> float:
        """
        Arguments:
            unit: unit to return volumes in.

        Returns: total volume stored in slice in uL.
        """
        return self.get_volumes(unit=unit).sum()

    @staticmethod
    def transfer(source: Container | Plate | PlateSlicer, destination: Plate | PlateSlicer, quantity: str) \
            -> Tuple[Container | Plate | PlateSlicer, Plate]:
        """
        Move quantity ('10 mL', '5 mg') from source to destination,
        returning copies of the objects with amounts adjusted accordingly.

        Arguments:
            source: What to transfer.
            destination: Plate or slice of a plate to transfer to.
            quantity: How much to transfer.

        Returns:
            A tuple of (T, Plate) where T is the type of the source.
        """
        if not isinstance(destination, (Plate, PlateSlicer)):
            raise TypeError("You can only use Plate.transfer into a Plate")
        if isinstance(destination, Plate):
            destination = destination[:]
        # noinspection PyProtectedMember
        return PlateSlicer._transfer(source, destination, quantity)

    def remove(self, what=Substance.LIQUID) -> Plate:
        """
        Removes substances from `Plate`

        Arguments:
            what: What to remove. Can be a type of substance or a specific substance. Defaults to LIQUID.

        Returns: New Plate with requested substances removed.

        """
        return self[:].remove(what)

    def fill_to(self, solvent, quantity):
        """
        Fills all wells in plate with `solvent` up to `quantity`.

        Args:
            solvent: Substance to use to fill.
            quantity: Desired final quantity in each well.

        Returns: New Plate with desired final `quantity` in each well.

        """
        return self[:].fill_to(solvent, quantity)


class RecipeStep:
    """
    Stores information about a single step in a recipe.

    Notes: The contents of this class are not meant to be consumed directly by users. Information about the step can be
    extracted using the `dataframe` and `_repr_html_` methods. If a step is displayed in IPython (Jupyter),
    `_repr_html_` will be called automatically.

    """

    def __init__(self, recipe: Recipe, operator: str, frm: Container | PlateSlicer | Plate,
                 to: Container | PlateSlicer | Plate, *operands):
        """
        Creates a new RecipeStep.
        """
        self.frm_slice = None
        self.to_slice = None
        self.recipe = recipe
        self.objects_used = set()
        self.substances_used = set()
        self.operator = operator
        self.frm: list[Container | PlateSlicer | Plate | None] = [frm]
        self.to: list[Container | PlateSlicer | Plate] = [to]
        self.trash = {}
        self.operands = operands
        self.instructions = ""

    def _repr_html_(self):
        """
        Returns: HTML representation of the step.
        """
        precision = config.precisions[config.volume_display_unit] if config.volume_display_unit in config.precisions \
            else config.precisions['default']
        source_visual = None
        if isinstance(self.frm[0], Container):
            source_visual = self.frm[0].dataframe()
        elif isinstance(self.frm[0], Plate):
            if self.frm_slice is None:
                source_visual = self.frm[0].dataframe()
            else:
                frm_slice: PlateSlicer = copy(self.frm_slice)
                frm_slice.plate = self.frm[0]
                source_visual = frm_slice.dataframe(highlight=True)
        destination_visual = None
        if isinstance(self.to[0], Container):
            destination_visual = self.to[1].dataframe()
        elif isinstance(self.to[0], Plate):
            if self.to_slice is None:
                before = self.to[0].dataframe()
                after = self.to[1].dataframe()
            else:
                to_slice: PlateSlicer = copy(self.to_slice)
                to_slice.plate = self.to[0]
                before = to_slice.dataframe()
                to_slice.plate = self.to[1]
                after = to_slice.dataframe()
            delta_data = after.data - before.data
            destination_visual = delta_data.style.format(precision=precision).use(before.export())
            vmin = min(delta_data.min().min(), 0)
            vmax = Unit.convert_from_storage(self.to[0].max_volume_per_well, config.volume_display_unit)
            cmap = config.default_colormap if vmin >= 0 and vmax >= 0 else config.default_diverging_colormap
            destination_visual = destination_visual.background_gradient(cmap=cmap, vmin=vmin, vmax=vmax)

        if isinstance(source_visual, pandas.DataFrame):
            source_visual = source_visual.style
        if isinstance(destination_visual, pandas.DataFrame):
            destination_visual = destination_visual.style

        label = f"Destination (delta) ({config.volume_display_unit}): " if isinstance(self.to[0],
                                                                                      Plate) else "Destination: "
        destination_visual.set_caption(label + self.to[0].name)
        if source_visual is None:
            return self.instructions + '<br/>' + destination_visual.to_html()

        # source_visual.set_table_attributes("style='display:inline; margin-right:20px'")
        source_visual.set_table_attributes("style='width: 40%'")
        if isinstance(self.frm[0], Plate):
            source_visual.set_caption(f"Source (initial) ({config.volume_display_unit}): {self.frm[0].name}")
        else:
            source_visual.set_caption(f"Source (initial): {self.frm[0].name}")
        # destination_visual.set_table_attributes("style='display:inline'")
        destination_visual.set_table_attributes("style='width: 40%'")
        return (self.instructions + '<div style="display: flex; justify-content: space-evenly">' +
                source_visual.to_html() +
                destination_visual.to_html() + '</div>')

        # return self.instructions + '<br/>' + source_visual.to_html() + destination_visual.to_html()

    def dataframe(self, data_source: str = 'destination', substance: str | Substance = 'all', mode: str = 'final',
                  container_mode: str = 'data', unit: str = None) -> pandas.DataFrame:
        """

        Arguments:
            data_source: Where to get data from. 'source' or 'destination'.
            substance: Substance or 'all' to display.
            mode: 'final' to display final state, 'delta' to display change.
            container_mode: 'info' for information about the container, 'data' for a dataframe of the container.
            unit: unit to display volumes in. Defaults to config.volume_display_unit.

        Returns: Dataframe of quantities in each well or the container.

        If the designated 'data_source' is a Container, 'container_mode' will designate what is returned.

        If 'info' is selected for 'container_mode', an informational representation of the final state of the
        Container will be returned. The 'substance', 'mode', and 'unit' arguments are ignored.

        If 'data' is selected, a dataframe with one row and column will be returned.

        """

        if unit is None:
            unit = config.volume_display_unit

        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")

        if substance != 'all' and not isinstance(substance, Substance):
            raise TypeError("Substance must be a Substance or 'all'.")

        if data_source == 'source':
            before = self.frm[0]
            after = self.frm[1]
        elif data_source == 'destination':
            before = self.to[0]
            after = self.to[1]
        else:
            raise ValueError("Invalid data source.")

        if isinstance(before, Container):
            if container_mode == 'info':
                return after.dataframe()
            elif container_mode == 'data':
                if substance == 'all':
                    before = pandas.DataFrame([before.get_volume(unit)], columns=[before.name])
                    after = pandas.DataFrame([after.get_volume(unit)], columns=[after.name])
                else:
                    from_unit = 'U' if isinstance(substance, Substance) and substance.is_enzyme() else 'mol'
                    before = pandas.DataFrame([Unit.convert_from(substance, before.contents.get(substance, 0), from_unit, unit)],
                                              columns=[before.name])
                    after = pandas.DataFrame([Unit.convert_from(substance, after.contents.get(substance, 0), from_unit, unit)],
                                             columns=[after.name])
        else:
            before = before.dataframe(substance=substance, unit=unit).data
            after = after.dataframe(substance=substance, unit=unit).data

        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']

        if mode == 'final':
            return after.round(precision)
        elif mode == 'delta':
            return (after - before).round(precision)
        else:
            raise ValueError("Invalid mode.")


class Recipe:
    """
    A list of instructions for transforming one set of containers into another. The intended workflow is to declare
    the source containers, enumerate the desired transformations, and call recipe.bake(). The name of each object used
    by the Recipe must be unique. This method will ensure that all solid and liquid handling instructions are valid.
    If they are indeed valid, then the updated containers will be generated. Once recipe.bake() has been called, no
    more instructions can be added and the Recipe is considered immutable.

    Attributes:
        locked (boolean): Is the recipe locked from changes?
        steps (list): A list of steps to be completed upon bake() bring called.
        used (list): A list of Containers and Plates to be used in the recipe.
        results (dict): A dictionary used in bake to return the mutated objects.
        stages (dict): A dictionary of stages in the recipe.
    """

    def __init__(self):
        self.results: dict[str, Container | Plate | PlateSlicer] = {}
        self.steps: list[RecipeStep] = []
        self.stages: dict[str, slice] = {'all': slice(None, None)}
        self.current_stage = 'all'
        self.current_stage_start = 0
        self.locked = False
        self.used = set()

    def start_stage(self, name: str) -> None:
        """
        Start a new stage in the recipe.

        Args:
            name: Name of the stage.

        """
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        if name in self.stages:
            raise ValueError("Stage name already exists.")
        if self.current_stage != 'all':
            raise ValueError("Cannot start a new stage without ending the current one.")
        self.current_stage = name
        self.current_stage_start = len(self.steps)

    def end_stage(self, name: str) -> None:
        """
        End the current stage in the recipe.

        Args:
            name: Name of the stage.

        """
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        if self.current_stage != name:
            raise ValueError("Current stage does not match name.")

        self.stages[name] = slice(self.current_stage_start, len(self.steps))
        self.current_stage = 'all'

    def uses(self, *args: Container | Plate | Iterable[Container | Plate]) -> Recipe:
        """
        Declare *args (iterable of Containers and Plates) as being used in the recipe.
        """
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        for arg in args:
            if isinstance(arg, (Container, Plate)):
                if arg.name not in self.results:
                    self.results[arg.name] = deepcopy(arg)
                else:
                    raise ValueError(f"An object with the name: \"{arg.name}\" is already in use.")
            elif isinstance(arg, Iterable):
                unpacked = list(arg)
                if not all(isinstance(elem, (Container, Plate)) for elem in unpacked):
                    raise TypeError("Invalid type in iterable.")
                self.uses(*unpacked)
            else:
                raise TypeError("Invalid type.")
        return self

    def transfer(self, source: Container | Plate | PlateSlicer, destination: Container | Plate | PlateSlicer,
                 quantity: str) -> None:
        """
        Adds a step to the recipe which will move quantity from source to destination.
        Note that all Substances in the source will be transferred in proportion to their respective ratios.

        """
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        if not isinstance(destination, (Container, Plate, PlateSlicer)):
            raise TypeError("Invalid destination type.")
        if not isinstance(source, (Container, Plate, PlateSlicer)):
            raise TypeError("Invalid source type.")
        if (source.plate.name if isinstance(source, PlateSlicer) else source.name) not in self.results:
            raise ValueError("Source not found in declared uses.")
        destination_name = destination.plate.name if isinstance(destination, PlateSlicer) else destination.name
        if destination_name not in self.results:
            raise ValueError(f"Destination {destination_name} has not been previously declared for use.")
        if not isinstance(quantity, str):
            raise TypeError("Volume must be a str. ('5 mL')")
        if isinstance(source, Plate):
            source = source[:]
        if isinstance(destination, Plate):
            destination = destination[:]
        self.steps.append(RecipeStep(self, 'transfer', source, destination, quantity))

    def create_container(self, name: str, max_volume: str = 'inf L',
                         initial_contents: Iterable[tuple[Substance, str]] | None = None) -> Container:

        """
        Adds a step to the recipe which creates a container.

        Arguments:
            name: Name of container
            max_volume: Maximum volume that can be stored in the container. ('10 mL')
            initial_contents: (optional) Iterable of tuples of the form (Substance, quantity)

        Returns:
            A new Container so that it may be used in later recipe steps.
        """
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        if not isinstance(max_volume, str):
            raise TypeError("Maximum volume must be a str.")

        if initial_contents:
            if not isinstance(initial_contents, Iterable):
                raise TypeError("Initial contents must be iterable.")
            if not all(isinstance(elem, tuple) and len(elem) == 2 for elem in initial_contents):
                raise TypeError("Elements of initial_contents must be of the form (Substance, quantity.)")
            for substance, quantity in initial_contents:
                if not isinstance(substance, Substance):
                    raise TypeError("Containers can only be created from substances.")
                if not isinstance(quantity, str):
                    raise TypeError("Quantity must be a str. ('10 mL')")
        new_container = Container(name, max_volume)
        self.uses(new_container)
        self.steps.append(RecipeStep(self, 'create_container', None, new_container, max_volume, initial_contents))

        return new_container

    def create_solution(self, solute: Substance | Iterable[Substance], solvent: Substance | Container,
                        name=None, **kwargs) -> Container:
        """
        Adds a step to the recipe which creates a solution.

        Two out of concentration, quantity, and total_quantity must be specified.

        Multiple solutes can be, optionally, provided as a list. Each solute will have the desired concentration
        or quantity in the final solution.

        If one value is specified for concentration or quantity and multiple solutes are provided, the value will be
        used for all solutes.

        Arguments:
            solute: What to dissolve. Can be a single Substance or an iterable of Substances.
            solvent: What to dissolve with. Can be a Substance or a Container.
            name: Optional name for new container.
            concentration: Desired concentration(s). ('1 M', '0.1 umol/10 uL', etc.)
            quantity: Desired quantity of solute(s). ('3 mL', '10 g')
            total_quantity: Desired total quantity. ('3 mL', '10 g')


        Returns:
            A new Container so that it may be used in later recipe steps.
        """

        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(solvent, Substance):
            raise TypeError("Solvent must be a Substance.")
        if name and not isinstance(name, str):
            raise TypeError("Name must be a str.")

        if 'concentration' in kwargs and not isinstance(kwargs['concentration'], str):
            raise TypeError("Concentration must be a str.")
        if 'quantity' in kwargs and not isinstance(kwargs['quantity'], str):
            raise TypeError("Quantity must be a str.")
        if 'total_quantity' in kwargs and not isinstance(kwargs['total_quantity'], str):
            raise TypeError("Total quantity must be a str.")
        if ('concentration' in kwargs) + ('total_quantity' in kwargs) + ('quantity' in kwargs) != 2:
            raise ValueError("Must specify two values out of concentration, quantity, and total quantity.")

        if not name:
            name = f"solution of {solute.name} in {solvent.name}"

        new_container = Container(name)
        self.uses(new_container)
        self.steps.append(RecipeStep(self, 'solution', None, new_container, solute, solvent, kwargs))

        return new_container

    def create_solution_from(self, source: Container, solute: Substance, concentration: str, solvent: Substance,
                             quantity: str, name=None) -> Container:
        """
        Adds a step to create a diluted solution from an existing solution.


        Arguments:
            source: Solution to dilute.
            solute: What to dissolve.
            concentration: Desired concentration. ('1 M', '0.1 umol/10 uL', etc.)
            solvent: What to dissolve with.
            quantity: Desired total quantity. ('3 mL', '10 g')
            name: Optional name for new container.

        Returns:
            A new Container so that it may be used in later recipe steps.
        """

        if not isinstance(source, Container):
            raise TypeError("Source must be a Container.")
        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(concentration, str):
            raise TypeError("Concentration must be a str.")
        if not isinstance(solvent, Substance):
            raise TypeError("Solvent must be a Substance.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")
        if name and not isinstance(name, str):
            raise TypeError("Name must be a str.")

        quantity_value, quantity_unit = Unit.parse_quantity(quantity)
        if quantity_value <= 0:
            raise ValueError("Quantity must be positive.")

        if not name:
            name = f"solution of {solute.name} in {solvent.name}"

        new_ratio, numerator, denominator = Unit.calculate_concentration_ratio(solute, concentration, solvent)
        if new_ratio <= 0:
            raise ValueError("Solution is impossible to create.")

        new_container = Container(name, max_volume=f"{source.max_volume} {config.volume_storage_unit}")
        self.uses(new_container)
        self.steps.append(RecipeStep(self, 'solution_from', source, new_container,
                                     solute, concentration, solvent, quantity))

        return new_container

    def remove(self, destination: Container | Plate | PlateSlicer, what=Substance.LIQUID) -> None:
        """
        Adds a step to removes substances from destination.

        Arguments:
            destination: What to remove from.
            what: What to remove. Can be a type of substance or a specific substance. Defaults to LIQUID.
        """

        if isinstance(destination, PlateSlicer):
            if destination.plate.name not in self.results:
                raise ValueError(f"Destination {destination.plate.name} has not been previously declared for use.")
        elif isinstance(destination, (Container, Plate)):
            if destination.name not in self.results:
                raise ValueError(f"Destination {destination.name} has not been previously declared for use.")
        else:
            raise TypeError(f"Invalid destination type: {type(destination)}")

        self.steps.append(RecipeStep(self, 'remove', None, destination, what))

    def dilute(self, destination: Container, solute: Substance,
               concentration: str, solvent: Substance, new_name=None) -> None:
        """
        Adds a step to dilute `solute` in `destination` to `concentration`.

        Args:
            destination: Container to dilute.
            solute: Substance which is subject to dilution.
            concentration: Desired concentration in mol/L.
            solvent: What to dilute with.
            new_name: Optional name for new container.
        """

        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(concentration, str):
            raise TypeError("Concentration must be a float.")
        if not isinstance(solvent, Substance):
            raise TypeError("Solvent must be a substance.")
        if new_name and not isinstance(new_name, str):
            raise TypeError("New name must be a str.")
        if not isinstance(destination, Container):
            raise TypeError("Destination must be a container.")
        if destination.name not in self.results:
            raise ValueError(f"Destination {destination.name} has not been previously declared for use.")
        # if solute not in destination.contents:
        #     raise ValueError(f"Container does not contain {solute.name}.")

        ratio, *_ = Unit.calculate_concentration_ratio(solute, concentration, solvent)
        if ratio <= 0:
            raise ValueError("Concentration is impossible to create.")

        if solute.is_enzyme():
            # TODO: Support this.
            raise ValueError("Not currently supported.")

        self.steps.append(RecipeStep(self, 'dilute', None, destination, solute, concentration, solvent, new_name))

    def fill_to(self, destination: Container | Plate | PlateSlicer, solvent: Substance, quantity: str) -> None:
        """
        Adds a step to fill `destination` container/plate/slice with `solvent` up to `quantity`.

        Args:
            destination: Container/Plate/Slice to fill.
            solvent: Substance to use to fill.
            quantity: Desired final quantity in container.

        """
        if isinstance(destination, PlateSlicer):
            if destination.plate.name not in self.results:
                raise ValueError(f"Destination {destination.plate.name} has not been previously declared for use.")
        elif isinstance(destination, (Container, Plate)):
            if destination.name not in self.results:
                raise ValueError(f"Destination {destination.name} has not been previously declared for use.")
        else:
            raise TypeError(f"Invalid destination type: {type(destination)}")
        if not isinstance(solvent, Substance):
            raise TypeError("Solvent must be a substance.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")

        self.steps.append(RecipeStep(self, 'fill_to', None, destination, solvent, quantity))

    def bake(self) -> dict[str, Container | Plate]:
        """
        Completes steps stored in recipe.
        Checks validity of each step and ensures all declared objects have been used.
        Locks Recipe from further modification.

        Returns:
            Copies of all used objects in the order they were declared.

        """
        if self.locked:
            raise RuntimeError("Recipe has already been baked.")

        # Implicitly end the current stage
        if self.current_stage != 'all':
            self.end_stage(self.current_stage)

        for step in self.steps:
            # Keep track of what was used in each step
            for elem in step.frm + step.to:
                if isinstance(elem, PlateSlicer):
                    step.objects_used.add(elem.plate.name)
                elif isinstance(elem, (Container, Plate)):
                    step.objects_used.add(elem.name)

            step.frm_slice = step.frm[0] if isinstance(step.frm[0], PlateSlicer) else None
            step.to_slice = step.to[0] if isinstance(step.to[0], PlateSlicer) else None

            operator = step.operator
            if operator == 'create_container':
                dest = step.to[0]
                dest_name = dest.name
                step.frm.append(None)
                max_volume, initial_contents = step.operands
                step.to[0] = self.results[dest_name]
                self.used.add(dest_name)
                self.results[dest_name] = Container(dest_name, max_volume, initial_contents)
                step.substances_used = self.results[dest_name].get_substances()
                step.to.append(self.results[dest_name])
                step.instructions = f"Create container '{dest_name}'."
            elif operator == 'transfer':
                source = step.frm[0]
                source_name = source.plate.name if isinstance(source, PlateSlicer) else source.name
                dest = step.to[0]
                dest_name = dest.plate.name if isinstance(dest, PlateSlicer) else dest.name
                quantity, = step.operands

                step.instructions = f"""Transfer {quantity} from '{str(source) if isinstance(source, PlateSlicer) else
                source_name}' to '{str(dest) if isinstance(dest, PlateSlicer) else dest_name}'."""

                self.used.add(source_name)
                self.used.add(dest_name)

                # containers and such can change while baking the recipe
                if isinstance(source, PlateSlicer):
                    source = deepcopy(source)
                    source.plate = self.results[source_name]
                    step.frm[0] = source.plate
                else:
                    source = self.results[source_name]
                    step.frm[0] = source

                step.substances_used = source.get_substances()

                if isinstance(dest, PlateSlicer):
                    dest = deepcopy(dest)
                    dest.plate = self.results[dest_name]
                    step.to[0] = dest.plate
                else:
                    dest = self.results[dest_name]
                    step.to[0] = dest

                if isinstance(dest, Container):
                    source, dest = Container.transfer(source, dest, quantity)
                elif isinstance(dest, PlateSlicer):
                    source, dest = Plate.transfer(source, dest, quantity)

                self.results[source_name] = source if not isinstance(source, PlateSlicer) else source.plate
                self.results[dest_name] = dest if not isinstance(dest, PlateSlicer) else dest.plate

                step.frm.append(self.results[source_name])
                step.to.append(self.results[dest_name])
            elif operator == 'solution':
                dest = step.to[0]
                dest_name = dest.name
                step.frm.append(None)
                solute, solvent, kwargs = step.operands
                # kwargs should have two out of concentration, quantity, and total_quantity
                if 'concentration' in kwargs and 'total_quantity' in kwargs:
                    step.instructions = f"""Create a solution of '{solute.name}' in '{solvent.name
                    }' with a concentration of {kwargs['concentration']
                    } and a total quantity of {kwargs['total_quantity']}."""
                elif 'concentration' in kwargs and 'quantity' in kwargs:
                    step.instructions = f"""Create a solution of '{solute.name}' in '{solvent.name
                    }' with a concentration of {kwargs['concentration']
                    } and a quantity of {kwargs['quantity']}."""
                elif 'quantity' in kwargs and 'total_quantity' in kwargs:
                    step.instructions = f"""Create a solution of '{solute.name}' in '{solvent.name
                    }' with a total quantity of {kwargs['total_quantity']
                    } and a quantity of {kwargs['quantity']}."""

                step.to[0] = self.results[dest_name]
                self.used.add(dest_name)
                self.results[dest_name] = Container.create_solution(solute, solvent, dest_name, **kwargs)
                step.substances_used = self.results[dest_name].get_substances()
                step.to.append(self.results[dest_name])
            elif operator == 'solution_from':
                source = step.frm[0]
                source_name = source.name
                dest = step.to[0]
                dest_name = dest.name
                solute, concentration, solvent, quantity = step.operands
                step.frm[0] = self.results[source_name]
                step.to[0] = self.results[dest_name]
                step.instructions = f"""Create {quantity} of a {concentration} solution of '{solute.name
                }' in '{solvent.name}' from '{source_name}'."""
                self.used.add(source_name)
                self.used.add(dest_name)
                source = self.results[source_name]
                self.results[source_name], self.results[dest_name] = \
                    Container.create_solution_from(source, solute, concentration, solvent, quantity, dest.name)
                step.substances_used = self.results[dest_name].get_substances()
                step.frm.append(self.results[source_name])
                step.to.append(self.results[dest_name])
            elif operator == 'remove':
                dest = step.to[0]
                step.frm.append(None)
                what, = step.operands
                dest_name = dest.plate.name if isinstance(dest, PlateSlicer) else dest.name
                step.to[0] = self.results[dest_name]
                self.used.add(dest_name)

                if isinstance(dest, PlateSlicer):
                    dest = deepcopy(dest)
                    dest.plate = self.results[dest_name]
                else:
                    dest = self.results[dest_name]

                if isinstance(what, Substance):
                    step.instructions = f"Remove {what.name} from '{dest_name}'."
                else:
                    step.instructions = f"Remove all {Substance.classes[what]} from '{dest_name}'."
                self.results[dest_name] = dest.remove(what)
                step.to.append(self.results[dest_name])
                # substances_used is everything that is in step.to[0] but not in step.to[1]
                step.substances_used = set.difference(step.to[0].get_substances(), step.to[1].get_substances())
                if isinstance(dest, Container):
                    step.trash = {substance: step.to[0].contents[substance] for substance in step.substances_used}
                else:  # Plate
                    for well in step.to[0].wells.flatten():
                        for substance in step.substances_used:
                            step.trash[substance] = step.trash.get(substance, 0.) + well.contents.get(substance, 0.)
            elif operator == 'dilute':
                dest = step.to[0]
                dest_name = dest.name
                solute, concentration, solvent, new_name = step.operands
                step.frm.append(None)
                step.to[0] = self.results[dest_name]
                self.used.add(dest_name)
                self.results[dest_name] = self.results[dest_name].dilute(solute, concentration, solvent, new_name)
                amount_added = self.results[dest_name].contents[solvent] - step.to[0].contents.get(solvent, 0)
                amount_added = Unit.convert_from(solvent, amount_added, config.moles_storage_unit, 'L')
                amount_added, unit = Unit.get_human_readable_unit(amount_added, 'L')
                precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                step.instructions = (f"Dilute '{solute.name}' in '{dest_name}' to {concentration}" +
                                     f" by adding {round(amount_added, precision)} {unit} of '{solvent.name}'.")
                step.substances_used.add(solvent)
                step.to.append(self.results[dest_name])
            elif operator == 'fill_to':
                dest = step.to[0]
                dest_name = dest.plate.name if isinstance(dest, PlateSlicer) else dest.name
                solvent, quantity = step.operands
                step.frm.append(None)
                step.to[0] = self.results[dest_name]
                self.used.add(dest_name)
                self.results[dest_name] = step.to[0].fill_to(solvent, quantity)
                step.to.append(self.results[dest_name])
                if isinstance(dest, Container):
                    amount_added = self.results[dest_name].contents[solvent] - step.to[0].contents.get(solvent, 0)
                    amount_added = Unit.convert_from(solvent, amount_added, config.moles_storage_unit, 'L')
                    amount_added, unit = Unit.get_human_readable_unit(amount_added, 'L')
                    precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                    step.instructions = (f"Fill '{dest.name}' with '{solvent.name}' up to {quantity}"
                                         f" by adding {round(amount_added, precision)} {unit}.")
                else:  # PlateSlicer
                    def collapse(wells, plate):
                        result = []
                        row_run = col_run = None
                        start_well = end_well = wells[0]
                        for well in wells[1:]:
                            if row_run is not None:
                                if well[0] == row_run and well[1] == end_well[1] + 1:
                                    end_well = well
                                else:
                                    row_run = None
                                    result.append(
                                        f"{plate.row_names[start_well[0]]}{plate.column_names[start_well[1]]}:"
                                        f"{plate.row_names[end_well[0]]}{plate.column_names[end_well[1]]}")
                                    start_well = end_well = well
                            elif col_run is not None:
                                if well[1] == col_run and well[0] == end_well[0] + 1:
                                    end_well = well
                                else:
                                    col_run = None
                                    result.append(
                                        f"{plate.row_names[start_well[0]]}{plate.column_names[start_well[1]]}:"
                                        f"{plate.row_names[end_well[0]]}{plate.column_names[end_well[1]]}")
                                    start_well = end_well = well
                            elif well[0] == end_well[0] and well[1] == end_well[1] + 1:
                                end_well = well
                                row_run = well[0]
                            elif well[1] == end_well[1] and well[0] == end_well[0] + 1:
                                end_well = well
                                col_run = well[1]
                            else:
                                result.append(f"{plate.row_names[start_well[0]]}{plate.column_names[start_well[1]]}")
                                start_well = end_well = well
                        if row_run is not None or col_run is not None:
                            result.append(f"{plate.row_names[start_well[0]]}{plate.column_names[start_well[1]]}:"
                                          f"{plate.row_names[end_well[0]]}{plate.column_names[end_well[1]]}")
                        if start_well == end_well:
                            result.append(f"{plate.row_names[start_well[0]]}{plate.column_names[start_well[1]]}")
                        return result

                    amounts = dict()
                    plate = step.to[0]
                    for row in range(plate.n_rows):
                        for col in range(plate.n_columns):
                            amount_added = self.results[dest_name].wells[row, col].contents[solvent] - \
                                           plate.wells[row, col].contents.get(solvent, 0)
                            amount_added = Unit.convert_from(solvent, amount_added, config.moles_storage_unit, 'uL')
                            amounts[(row, col)] = round(amount_added, config.internal_precision)
                    max_amount = max(amounts.values())
                    _, unit = Unit.get_human_readable_unit(max_amount / 1e6, 'L')
                    multiplier = 1e-6 / Unit.convert_prefix_to_multiplier(unit[:-1])
                    precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
                    amounts_transpose = dict()
                    for address, amount in amounts.items():
                        amount = round(amount * multiplier, precision)
                        if amount == 0.:
                            continue
                        if amount not in amounts_transpose:
                            amounts_transpose[amount] = []
                        amounts_transpose[amount].append(address)
                    step.instructions = f"Fill '{dest.name}' with '{solvent.name}' up to {quantity} by adding: "
                    amount_strings = []
                    for amount, addresses in amounts_transpose.items():
                        addresses = collapse(addresses, plate)
                        amount_strings.append(f"{amount} {unit} to [{', '.join(addresses)}]")
                    step.instructions += ', '.join(amount_strings) + "."

                if isinstance(dest, PlateSlicer):
                    dest = deepcopy(dest)
                    dest.plate = self.results[dest_name]
                else:
                    dest = self.results[dest_name]

                self.results[dest_name] = dest.fill_to(solvent, quantity)
                step.substances_used.add(solvent)
                step.to.append(self.results[dest_name])

        if len(self.used) != len(self.results):
            raise ValueError("Something declared as used wasn't used.")
        self.locked = True
        # All the PlateSlicers should have been resolved into Plates by now
        assert all(isinstance(elem, (Container, Plate)) for elem in self.results.values())
        return self.results

    def get_substance_used(self, substance: Substance, timeframe: str = 'all', unit: str = None,
                           destinations: Iterable[Container | Plate] | str = "plates"):
        """
        Returns the amount of substance used in the recipe.

        Args:
            substance: Substance to check.
            timeframe: 'before' or 'during'. Before refers to the initial state of the containers aka recipe "prep", and
            during refers to
            unit: Unit to return amount in.
            destinations: Containers or plates to check. Defaults to "plates".

        Returns: Amount of substance used in the recipe.

        """
        if unit is None:
            unit = 'U' if substance.is_enzyme() else config.moles_display_unit

        from_unit = 'U' if substance.is_enzyme() else config.moles_storage_unit

        dest_names = set()
        if destinations == "plates":
            dest_names = set(elem.name for elem in self.results.values() if isinstance(elem, Plate))
        elif isinstance(destinations, Iterable):
            for container in destinations:
                if container.name not in self.used:
                    raise ValueError(f"Destination {container.name} was not used in the recipe.")
                dest_names.add(container.name)
        else:
            raise ValueError("Invalid destinations.")

        delta = 0

        if timeframe not in self.stages.keys():
            raise ValueError("Invalid timeframe")

        stage_steps = self.steps[self.stages[timeframe]]
        for step in stage_steps:
            if substance not in step.substances_used:
                continue

            before_substances = 0
            after_substances = 0
            if step.to[0] is not None and step.to[0].name in dest_names:
                if isinstance(step.to[0], Plate):
                    before_substances += sum(well.contents.get(substance, 0) for well in step.to[0].wells.flatten())
                    after_substances += sum(well.contents.get(substance, 0) for well in step.to[1].wells.flatten())
                else:  # Container
                    before_substances += step.to[0].contents.get(substance, 0)
                    after_substances += step.to[1].contents.get(substance, 0)
            if step.frm[0] is not None and step.frm[0].name in dest_names:
                if isinstance(step.frm[0], Plate):
                    before_substances += sum(well.contents.get(substance, 0) for well in step.frm[0].wells.flatten())
                    after_substances += sum(well.contents.get(substance, 0) for well in step.frm[1].wells.flatten())
                else:  # Container
                    before_substances += step.frm[0].contents.get(substance, 0)
                    after_substances += step.frm[1].contents.get(substance, 0)
            after_substances += step.trash.get(substance, 0)
            delta += after_substances - before_substances

        if delta < 0:
            raise ValueError(
                f"Destination containers contain {-delta} {from_unit} less of substance {substance}" +
                " after stage {timeframe}. Did you specify the correct destinations?")
        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        return round(Unit.convert(substance, f'{delta} {from_unit}', unit), precision)

    def get_container_flows(self, container: Container | Plate, timeframe: str = 'all', unit: str | None = None) -> \
            dict[str, (int | str)]:
        """
        Returns the inflow and outflow of a container in the recipe.

        Args:
            container: Container to check.
            timeframe: 'all' or a stage defined in the recipe.
            unit: Unit to return amount in.
        """

        def helper(entry):
            substance, quantity = entry
            return Unit.convert_from(substance, quantity, 'U' if substance.is_enzyme() else config.moles_storage_unit,
                                     unit)

        def plate_helper(container):
            entry = container.contents.items()
            return sum(map(helper, entry))

        if unit is None:
            unit = config.volume_display_unit
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")
        if not isinstance(container, Container) and not isinstance(container, Plate):
            raise TypeError("Container must be a Container or a Plate.")
        if not isinstance(timeframe, str):
            raise TypeError("Timeframe must be a str.")
        if timeframe not in self.stages.keys():
            raise ValueError("Invalid Timeframe")
        steps = self.steps[self.stages[timeframe]]
        flows = {"in": 0, "out": 0}
        if isinstance(container, Plate):
            flows = {"in": np.zeros(container.wells.shape), "out": np.zeros(container.wells.shape)}
        for step in steps:
            if container.name in step.objects_used:
                if isinstance(step.to[0], Container) and step.to[0].name == container.name:
                    if step.trash:
                        flows["out"] += sum(map(helper, step.trash.items()))
                    else:
                        flows["in"] += (sum(map(helper, step.to[1].contents.items())) -
                                        sum(map(helper, step.to[0].contents.items())))
                if isinstance(step.to[0], Plate) and step.to[0].name == container.name:
                    if step.trash:
                        flows["out"] += sum(map(helper, step.trash.items()))
                    else:
                        vfunc = np.vectorize(plate_helper)
                        flows["in"] += vfunc(step.to[1].wells) - vfunc(step.to[0].wells)
                if isinstance(step.frm[0], Container) and step.frm[0].name == container.name:
                    flows["out"] += (sum(map(helper, step.frm[0].contents.items())) -
                                     sum(map(helper, step.frm[1].contents.items())))
                if isinstance(step.frm[0], Plate) and step.frm[0].name == container.name:
                    vfunc = np.vectorize(plate_helper)
                    flows["out"] += vfunc(step.frm[0].wells) - vfunc(step.frm[1].wells)
        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        for key in flows:
            flows[key] = round(flows[key], precision)

        return flows

    def get_amount_remaining(self, container: Container | Plate, timeframe: str = 'all',
                             unit: str | None = None, mode: str = 'after') -> float:

        def conversion_helper(entry):
            substance, quantity = entry
            return Unit.convert_from(substance, quantity, 'U' if substance.is_enzyme() else config.moles_storage_unit,
                                     unit)

        def plate_helper(well):
            entry = well.contents.items()
            return sum(map(conversion_helper, entry))

        def container_helper(container):
            if isinstance(container, Container):
                entry = container.contents.items()
                return sum(map(conversion_helper, entry))
            elif isinstance(container, Plate):
                vfunc = np.vectorize(plate_helper)
                return vfunc(container.wells)

        if unit is None:
            unit = config.volume_display_unit
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")
        if not isinstance(container, Container) and not isinstance(container, Plate):
            raise TypeError("Container must be a Container or a Plate.")
        if not isinstance(timeframe, str):
            raise TypeError("Timeframe must be a str.")
        if timeframe not in self.stages.keys():
            raise ValueError("Invalid Timeframe")

        steps = self.steps[self.stages[timeframe]]
        if mode == 'after':
            steps = reversed(steps)

        query_container = None
        for step in steps:
            if container.name in step.objects_used:
                if step.to[0].name == container.name:
                    if mode == 'after':
                        query_container = step.to[1]
                    else:
                        query_container = step.to[0]
                else:
                    if mode == 'after':
                        query_container = step.frm[1]
                    else:
                        query_container = step.frm[0]
                return container_helper(query_container)

    def visualize(self, what: Plate, mode: str, unit: str, timeframe: (int | str | RecipeStep) = 'all',
                  substance: (str | Substance) = 'all', cmap: str = None) \
            -> str | pandas.io.formats.style.Styler:
        """

        Provide visualization of what happened during the step.

        Args:
            what: Plate we are interested in.
            mode: 'delta', or 'final'
            timeframe: Number of the step or the name of the stage to visualize.
            unit: Unit we are interested in. ('mmol', 'uL', 'mg')
            substance: Substance we are interested in. ('all', water, ATP)
            cmap: Colormap to use. Defaults to default_colormap from config.

        Returns: A dataframe with the requested information.
        """
        if not isinstance(what, Plate):
            raise TypeError("What must be a Plate.")
        if mode not in ['delta', 'final']:
            raise ValueError("Invalid mode.")
        if not isinstance(timeframe, (int, str, RecipeStep)):
            raise TypeError("When must be an int or str.")
        if isinstance(timeframe, str) and timeframe not in self.stages:
            raise ValueError("Invalid stage.")
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")
        if substance != 'all' and not isinstance(substance, Substance):
            raise TypeError("Substance must be a Substance or 'all'")
        if cmap is None:
            cmap = config.default_colormap
        if not isinstance(cmap, str):
            raise TypeError("Colormap must be a str.")

        def helper(elem):
            """ Returns amount of substance in elem. """
            if substance == 'all':
                amount = 0
                for subst, quantity in elem.contents.items():
                    substance_unit = 'U' if subst.is_enzyme() else config.moles_storage_unit
                    amount += Unit.convert_from(subst, quantity, substance_unit, unit)
                return amount
            else:
                substance_unit = 'U' if substance.is_enzyme() else config.moles_storage_unit
                return Unit.convert_from(substance, elem.contents.get(substance, 0), substance_unit, unit)

        if isinstance(timeframe, RecipeStep):
            start_index = self.steps.index(timeframe)
            end_index = start_index + 1
        elif isinstance(timeframe, str):
            start_index = self.stages[timeframe].start
            end_index = self.stages[timeframe].stop
            if start_index is None:
                start_index = 0
            if end_index is None:
                end_index = len(self.steps)
        else:
            if timeframe >= len(self.steps):
                raise ValueError("Invalid step number.")
            if timeframe < 0:
                timeframe = max(0, len(self.steps) + timeframe)
            start_index = timeframe
            end_index = timeframe + 1

        start = None
        end = None
        for i in range(start_index, end_index):
            step = self.steps[i]
            if what.name in step.objects_used:
                start = i
                break
        for i in range(end_index - 1, start_index - 1, -1):
            step = self.steps[i]
            if what.name in step.objects_used:
                end = i
                break
        if start is None or end is None:
            return "This plate was not used in the specified timeframe."

        if mode == 'delta':
            before_data = None
            if what.name == self.steps[start].frm[0].name:
                before_data = self.steps[start].frm[0][:].get_dataframe()
            elif what.name == self.steps[start].to[0].name:
                before_data = self.steps[start].to[0][:].get_dataframe()
            before_data = before_data.applymap(numpy.vectorize(helper, cache=True, otypes='d'))
            after_data = None
            if what.name == self.steps[end].frm[1].name:
                after_data = self.steps[end].frm[1][:].get_dataframe()
            elif what.name == self.steps[end].to[1].name:
                after_data = self.steps[end].to[1][:].get_dataframe()
            after_data = after_data.applymap(numpy.vectorize(helper, cache=True, otypes='d'))
            df = after_data - before_data
        else:
            data = None
            if what.name == self.steps[end].frm[1].name:
                data = self.steps[end].frm[1][:].get_dataframe()
            elif what.name == self.steps[end].to[1].name:
                data = self.steps[end].to[1][:].get_dataframe()
            df = data.applymap(numpy.vectorize(helper, cache=True, otypes='d'))

        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        df = df.round(precision)
        vmin, vmax = df.min().min(), df.max().max()
        styler = df.style.format(precision=precision).background_gradient(cmap, vmin=vmin, vmax=vmax)
        return styler


class PlateSlicer(Slicer):
    """
    Represents a slice of a Plate.
    """

    def __init__(self, plate, item):
        self.plate = plate
        super().__init__(plate.wells, plate.row_names, plate.column_names, item)

    def _get_slice_string(self, item):
        assert isinstance(item, tuple)
        left, right = item
        if left.start is None and left.stop is None and right.start is None and right.stop is None:
            return ':'
        if left.start is None:
            left = slice(0, left.stop)
        if left.stop is None:
            left = slice(left.start, len(self.plate.row_names))
        if right.start is None:
            right = slice(0, right.stop)
        if right.stop is None:
            right = slice(right.start, len(self.plate.column_names))
        if left.stop == left.start + 1 and right.stop == right.start + 1:
            return f"'{self.plate.row_names[left.start]}:{self.plate.column_names[right.start]}'"
        else:
            if left.start == 0 and left.stop == len(self.plate.row_names):
                left = ':'
            else:
                left = f"'{self.plate.row_names[left.start]}':'{self.plate.row_names[left.stop - 1]}'"
            if right.start == 0 and right.stop == len(self.plate.column_names):
                right = ':'
            else:
                right = f"'{self.plate.column_names[right.start]}':'{self.plate.column_names[right.stop - 1]}'"
            if right == ':':
                return left
            else:
                return f"{left}, {right}"

    def __repr__(self):
        if isinstance(self.slices, list):
            result = f"[{', '.join([self._get_slice_string(item) for item in self.slices])}]"
        else:
            result = self._get_slice_string(self.slices)
        return f"{self.plate.name}[{result}]"

    @property
    def name(self):
        return self.__repr__()

    @property
    def array(self):
        """ @private """
        return self.plate.wells

    @array.setter
    def array(self, array: numpy.ndarray):
        self.plate.wells = array

    def get_dataframe(self):
        return pandas.DataFrame(self.plate.wells, columns=self.plate.column_names,
                                index=self.plate.row_names)

    @staticmethod
    def _transfer(frm: Container | PlateSlicer, to: PlateSlicer, quantity):
        if isinstance(frm, Container):
            to = copy(to)
            to.plate = deepcopy(to.plate)

            def helper_func(elem):
                """ @private """
                frm_array[0], elem = Container.transfer(frm_array[0], elem, quantity)
                return elem

            frm_array = [frm]
            to.apply(helper_func)
            return frm_array[0], to.plate
        if not isinstance(frm, (Plate, PlateSlicer)):
            raise TypeError("Invalid source type.")

        to = copy(to)
        frm = copy(frm)

        if to.plate != frm.plate:
            different = True
            to.plate = deepcopy(to.plate)
            frm.plate = deepcopy(frm.plate)
        else:
            different = False
            to.plate = frm.plate = deepcopy(to.plate)

        if frm.size == 1:
            # Source from the single element in frm
            if frm.shape != (1, 1):
                raise RuntimeError("Shape of source should have been (1, 1)")

            def helper_func(elem):
                """ @private """
                assert isinstance(frm_array, numpy.ndarray)
                frm_array[0, 0], elem = Container.transfer(frm_array[0, 0], elem, quantity)
                if different:
                    instructions = elem.instructions.splitlines()
                    instructions[-1] = instructions[-1].replace(frm_array[0, 0].name,
                                                                frm.plate.name + " " + frm_array[0, 0].name, 1)
                    elem.instructions = "\n".join(instructions)

                return elem

            frm_array = frm.get()
            to.apply(helper_func)

        elif to.size == 1:
            #  Replace the single element in self
            if to.shape != (1, 1):
                raise RuntimeError("Shape of source should have been (1, 1)")

            def helper_func(elem):
                """ @private """
                elem, to_array[0][0] = to_array[0][0].transfer(elem, quantity)
                instructions = to_array[0][0].instructions.splitlines()
                instructions[-1] = instructions[-1].replace(elem.name, frm.plate.name + " " + elem.name, 1)
                elem.instructions = "\n".join(instructions)
                return elem

            to_array = to.get()
            frm.apply(helper_func)

        elif frm.size == to.size and frm.shape == to.shape:
            def helper(elem1, elem2):
                """ @private """
                elem1, elem2 = Container.transfer(elem1, elem2, quantity)
                if different:
                    instructions = elem2.instructions.splitlines()
                    instructions[-1] = instructions[-1].replace(elem1.name, frm.plate.name + " " + elem1.name, 1)
                    elem2.instructions = "\n".join(instructions)
                return elem1, elem2

            func = numpy.frompyfunc(helper, 2, 2)
            frm_result, to_result = func(frm.get(), to.get())
            frm.set(frm_result)
            to.set(to_result)
        else:
            raise ValueError("Source and destination slices must be the same size and shape.")

        return frm.plate, to.plate

    def highlight_wells(self, styler: pandas.io.formats.style.Styler) -> pandas.io.formats.style.Styler:
        highlight_wells = []
        if isinstance(self.slices, list):
            for slice_ in self.slices:
                row = slice_[0].start or 0
                col = slice_[1].start or 0
                highlight_wells.append((row, self.plate.column_names[col]))
        else:
            row_start = self.slices[0].start or 0
            row_stop = self.slices[0].stop or len(self.plate.row_names)
            row_step = self.slices[0].step or 1
            col_start = self.slices[1].start or 0
            col_stop = self.slices[1].stop or len(self.plate.column_names)
            col_step = self.slices[1].step or 1

            for row in range(row_start, row_stop, row_step):
                for col in range(col_start, col_stop, col_step):
                    highlight_wells.append((row, self.plate.column_names[col]))

        def highlight_func(elem):
            return ['background-color: yellow' if (i, elem.name) in highlight_wells else '' for i, _ in enumerate(elem)]

        styler.apply(highlight_func)
        return styler

    def dataframe(self, unit: str = None, substance: (str | Substance | Iterable[Substance]) = 'all',
                  cmap: str = None, highlight: bool = False):
        """

        Arguments:
            unit: unit to return quantities in.
            substance: Substance or Substances to display quantity of.
            cmap: Colormap to shade dataframe with.
            highlight: Highlight wells in slice(s).

        Returns: Shaded dataframe of quantities in each well.

        """
        if unit is None:
            unit = config.volume_display_unit

        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")
        if (substance != 'all' and not isinstance(substance, Substance) and
                not (isinstance(substance, Iterable) and all(isinstance(x, Substance) for x in substance))):
            raise TypeError("Substance must be a Substance or 'all'")
        if cmap is None:
            cmap = config.default_colormap
        if not isinstance(cmap, str):
            raise TypeError("Colormap must be a str.")

        if ('/' in unit or unit[-1] == 'm' or unit[-1] == 'M') and substance == 'all':
            raise ValueError("Cannot display concentrations with respect to 'all' substances.")

        def helper(elem):
            if '/' in unit or unit[-1] == 'm' or unit[-1] == 'M':
                """ Returns concentration of substance in elem. """
                return elem.get_concentration(substance, unit)
            # else
            """ Returns amount of substance in elem. """
            if substance == 'all':
                amount = 0
                for subst, quantity in elem.contents.items():
                    substance_unit = 'U' if subst.is_enzyme() else config.moles_storage_unit
                    amount += Unit.convert_from(subst, quantity, substance_unit, unit)
                return amount
            elif isinstance(substance, Iterable):
                amount = 0
                for subst in substance:
                    substance_unit = 'U' if subst.is_enzyme() else config.moles_storage_unit
                    amount += Unit.convert_from(subst, elem.contents.get(subst, 0), substance_unit, unit)
                return amount
            else:
                substance_unit = 'U' if substance.is_enzyme() else config.moles_storage_unit
                return Unit.convert_from(substance, elem.contents.get(substance, 0), substance_unit, unit)

        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        df = self.get_dataframe().apply(numpy.vectorize(helper, cache=True, otypes='d'))
        styler = df.style.format(precision=precision)
        if highlight:
            styler = self.highlight_wells(styler)
        else:
            if unit[-1] == 'L':
                vmax = Unit.convert_from_storage(self.plate.max_volume_per_well, unit)
            else:
                vmax = df.max().max()
            styler = styler.background_gradient(cmap, vmin=0, vmax=vmax)
        return styler

    def get_volumes(self, substance: (Substance | Iterable[Substance]) = None, unit: str = None) -> numpy.ndarray:
        """

        Arguments:
            unit:  unit to return volumes in.
            substance: (optional) Substance to display volumes of.

        Returns:
            numpy.ndarray of volumes for each well in uL

        """
        if unit is None:
            unit = config.volume_display_unit

        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']

        if substance is None:
            return numpy.vectorize(lambda elem: elem.get_volume(unit),
                                   cache=True, otypes='d')(self.get()).round(precision)

        if isinstance(substance, Substance):
            substance = [substance]

        if not (substance is None or
                (isinstance(substance, Iterable) and all(isinstance(x, Substance) for x in substance))):
            raise TypeError("Substance must be a Substance or an Iterable of Substances.")
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")

        def helper(elem):
            amount = 0
            """ Returns volume of elem. """
            if substance is None:
                for subs, quantity in elem.contents.items():
                    substance_unit = 'U' if subs.is_enzyme() else config.moles_storage_unit
                    amount += Unit.convert_from(subs, quantity, substance_unit, unit)
            else:
                for subs in substance:
                    substance_unit = 'U' if subs.is_enzyme() else config.moles_storage_unit
                    amount += Unit.convert_from(subs, elem.contents.get(subs, 0), substance_unit, unit)
            return amount

        return numpy.vectorize(helper, cache=True, otypes='d')(self.get()).round(precision)

    def get_substances(self) -> set[Substance]:
        """

        Returns: A set of substances present in the plate.

        """
        substances_arr = numpy.vectorize(lambda elem: set(elem.contents.keys()), cache=True)(self.get())
        return set.union(*substances_arr.flatten())

    def get_moles(self, substance: (Substance | Iterable[Substance]), unit: str = 'mol') -> numpy.ndarray:
        """
        Arguments:
            unit: unit to return moles in. ('mol', 'mmol', 'umol', etc.)
            substance: Substance to display moles of.

        Returns: moles of substance in each well.
        """

        if isinstance(substance, Substance):
            substance = [substance]
        if unit is None:
            unit = config.moles_display_unit

        if not isinstance(substance, Iterable) or not all(isinstance(x, Substance) for x in substance):
            raise TypeError("Substance must be a Substance or an Iterable of Substances.")
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")

        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']

        def helper(elem):
            amount = 0
            for subs in substance:
                if not subs.is_enzyme():
                    amount += Unit.convert_from(subs, elem.contents.get(subs, 0), config.moles_storage_unit, unit)
            return amount

        return numpy.vectorize(helper, cache=True, otypes='d')(self.get()).round(precision)

    def remove(self, what: (Substance | int) = Substance.LIQUID):
        """
        Removes substances from slice

        Arguments:
            what: What to remove. Can be a type of substance or a specific substance. Defaults to LIQUID.

        Returns: New Plate with requested substances removed.

        """
        self.plate = deepcopy(self.plate)
        self.apply(lambda elem: elem.remove(what))
        return self.plate

    def fill_to(self, solvent: Substance, quantity: str):
        """
        Fills all wells in slice with `solvent` up to `quantity`.

        Args:
            solvent: Substance to use to fill.
            quantity: Desired final quantity in each well.

        Returns: New Plate with desired final `quantity` in each well.

        """
        self.plate = deepcopy(self.plate)
        self.apply(lambda elem: elem.fill_to(solvent, quantity))

        return self.plate
