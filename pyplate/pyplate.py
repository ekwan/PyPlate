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
All values returned to the user are rounded to config.external_precision for ease of use.
"""

# Allow typing reference while still building classes
from __future__ import annotations

from collections import defaultdict
from functools import cache
from typing import Tuple, Dict, Iterable
from copy import deepcopy, copy
import numpy
import numpy as np
import pandas

from pyplate.slicer import Slicer
from . import Config

config = Config()


class Unit:
    """
    @private

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
    def parse_concentration(concentration):
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
        if numerator[1] not in ('U', 'mol', 'L', 'g') or denominator[0] not in ('mol', 'L', 'g'):
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

        if from_unit == 'U' and not substance.is_enzyme():
            raise ValueError("Only enzymes can be measured in activity units. 'U'")

        for suffix in ['U', 'L', 'g', 'mol']:
            if from_unit.endswith(suffix):
                prefix = from_unit[:-len(suffix)]
                quantity *= Unit.convert_prefix_to_multiplier(prefix)
                from_unit = suffix
                break

        result = None
        if substance.is_enzyme() and not to_unit.endswith('U'):
            return 0
        if to_unit.endswith('U'):
            prefix = to_unit[:-1]
            if not substance.is_enzyme():
                return 0
            if not from_unit == 'U':
                raise ValueError("Enzymes can only be measured in activity units. 'U'")
            result = quantity
        elif to_unit.endswith('L'):
            prefix = to_unit[:-1]
            if from_unit == 'L':
                result = quantity
            elif from_unit == 'mol':
                # mol * g/mol / (g/mL)
                result_in_mL = quantity * substance.mol_weight / substance.density
                result = result_in_mL / 1000
            elif from_unit == 'g':
                # g / (g/mL)
                result_in_mL = quantity / substance.density
                result = result_in_mL / 1000
        elif to_unit.endswith('mol'):
            prefix = to_unit[:-3]
            if from_unit == 'L':
                value_in_mL = quantity * 1000
                # mL * g/mL / (g/mol)
                result = value_in_mL * substance.density / substance.mol_weight
            elif from_unit == 'mol':
                result = quantity
            elif from_unit == 'g':
                # g / (g/mol)
                result = quantity / substance.mol_weight
        elif to_unit.endswith('g'):
            prefix = to_unit[:-1]
            if from_unit == 'L':
                value_in_mL = quantity * 1000
                # mL * g/mL
                result = value_in_mL * substance.density
            elif from_unit == 'mol':
                # mol * g/mol
                result = quantity * substance.mol_weight
            elif from_unit == 'g':
                result = quantity
        else:
            raise ValueError("Only L, U, g, and mol are valid units.")

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
            result = value * prefix_value / Unit.convert_prefix_to_multiplier(config.volume_prefix[0])
        else:  # moles
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-3])
            result = value * prefix_value / Unit.convert_prefix_to_multiplier(config.moles_prefix[0])
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
            result = value * Unit.convert_prefix_to_multiplier(config.volume_prefix[0]) / prefix_value
        else:  # moles
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-3])
            result = value * Unit.convert_prefix_to_multiplier(config.moles_prefix[0]) / prefix_value
        return round(result, config.internal_precision)

    @staticmethod
    def convert_from_storage_to_standard_format(what, quantity: float):
        """
        Converts a quantity of a substance or container to a standard format.
        Example: (water, 1e6) -> (18.015, 'mL'), (NaCl, 1e6) -> (58.443, 'g')
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
                quantity *= Unit.convert_prefix_to_multiplier(config.moles_prefix[0]) * what.mol_weight
            elif what.is_liquid():
                unit = 'L'
                # convert moles to liters
                # molecular weight is in g/mol
                # density is in g/mL
                quantity *= (Unit.convert_prefix_to_multiplier(config.moles_prefix[0])
                             * what.mol_weight / what.density / 1e3)
            else:
                raise TypeError("Invalid type for what.")
        elif isinstance(what, Container):
            # Assume the container contains a liquid
            unit = 'L'
            quantity *= Unit.convert_prefix_to_multiplier(config.volume_prefix[0])
        else:
            raise TypeError("Invalid type for what.")

        multiplier = 1
        while quantity < 1 and multiplier > 1e-6:
            quantity *= 1e3
            multiplier /= 1e3
        quantity = round(quantity, config.external_precision)
        unit = {1: '', 1e-3: 'm', 1e-6: 'u'}[multiplier] + unit
        if round(quantity, config.external_precision) == 0:
            quantity = 0

        return quantity, unit

    @staticmethod
    def get_human_readable_unit(value: float, unit: str):
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
    def calculate_concentration_ratio(solute: Substance, concentration: str, solvent: Substance):
        """
        Helper function for dealing with concentrations.

        Returns: ratio of moles or Activity Units per mole storage unit ('umol', etc.).

        """
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

    @staticmethod
    def calculate_concentration_ratio_moles(solute: Substance, quantity: str, solvent: Substance):
        q, q_unit = Unit.parse_quantity(quantity)
        if q_unit not in ('g', 'L', 'mol'):
            raise ValueError("Invalid unit in quantity.")
        if q_unit == 'g':
            q /= solute.mol_weight
        elif q_unit == 'L':
            q *= solute.density
        return Unit.calculate_concentration_ratio(solute, f"{q} mol", solvent)


class Substance:
    """
    An abstract chemical or biological entity (e.g., reagent, enzyme, solvent, etc.). Immutable.
    Enzymes are assumed to require zero volume.

    Attributes:
        name: Name of substance.
        mol_weight: Molecular weight (g/mol).
        density: Density if `Substance` is a liquid (g/mL).
        concentration: Calculated concentration if `Substance` is a liquid (mol/mL).
        molecule: `cctk.Molecule` if provided.
    """
    # An attribute `classes` could be added to support classes of substances.
    SOLID = 1
    LIQUID = 2
    ENZYME = 3

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
        substance.density = config.solid_density
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
    def enzyme(name: str, molecule=None):
        """
        Creates an enzyme.

        Arguments:
            name: Name of enzyme.
            molecule: (optional) A cctk.Molecule

        Returns: New substance.

        """
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")

        return Substance(name, Substance.ENZYME, molecule)

    def is_solid(self):
        """
        Return true if `Substance` is a solid.
        """
        return self._type == Substance.SOLID

    def is_liquid(self):
        """
        Return true if `Substance` is a liquid.
        """
        return self._type == Substance.LIQUID

    def is_enzyme(self):
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
                contents.append(f"{quantity} {unit} of {substance.name}")
            self.instructions = f"Add {', '.join(contents)}"
            if self.max_volume != float('inf'):
                max_volume, unit = Unit.convert_from_storage_to_standard_format(self, self.max_volume)
                self.instructions += f" to a {max_volume} {unit} container."
            else:
                self.instructions += " to a container."
        else:
            if self.max_volume != float('inf'):
                max_volume, unit = Unit.convert_from_storage_to_standard_format(self, self.max_volume)
                self.instructions = f"Create a {max_volume} {unit} container."
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

        if source.is_enzyme():
            volume_to_add = 0
            amount_to_add = Unit.convert(source, quantity, 'U')
        else:
            volume_to_add = Unit.convert(source, quantity, config.volume_prefix)
            amount_to_add = Unit.convert(source, quantity, config.moles_prefix)
        if self.volume + volume_to_add > self.max_volume:
            raise ValueError("Exceeded maximum volume")
        self.volume = round(self.volume + volume_to_add, config.internal_precision)
        self.contents[source] = round(self.contents.get(source, 0) + amount_to_add, config.internal_precision)

    def _transfer(self, source_container: Container, quantity: str):
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
            total_mass = sum(Unit.convert(substance, f"{amount} {config.moles_prefix}", "g") for
                             substance, amount in source_container.contents.items())
            ratio = mass_to_transfer / total_mass
        elif unit == 'mol':
            moles_to_transfer = Unit.convert_to_storage(quantity_to_transfer, 'mol')
            total_moles = sum(amount for substance, amount in source_container.contents.items()
                              if not substance.is_enzyme())
            ratio = moles_to_transfer / total_moles
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
            mass = sum(Unit.convert(substance, f"{amount} {config.moles_prefix if not substance.is_enzyme() else 'U'}",
                                    "mg") for substance, amount in source_container.contents.items())
            transfer, unit = Unit.get_human_readable_unit(mass * ratio, 'mg')

        to.instructions += f"\nTransfer {transfer} {unit} of {source_container.name} to {to.name}"
        to.volume = round(sum(Unit.convert(substance, f"{amount} {config.moles_prefix}", config.volume_prefix) for
                              substance, amount in to.contents.items()), config.internal_precision)
        if to.volume > to.max_volume:
            raise ValueError(f"Exceeded maximum volume in {to.name}.")
        source_container.volume = sum(Unit.convert(substance, f"{amount} {config.moles_prefix}", config.volume_prefix)
                                      for substance, amount in source_container.contents.items())
        source_container.volume = round(source_container.volume, config.internal_precision)
        return source_container, to

    def _transfer_slice(self, source_slice: Plate or PlateSlicer, quantity: str):
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

    def __repr__(self):
        contents = []
        for substance, value in sorted(self.contents.items(), key=lambda elem: (elem[0]._type, -elem[1])):
            if substance.is_enzyme():
                contents.append(f"{substance}: {value} U")
            else:
                value, unit = Unit.get_human_readable_unit(Unit.convert_from_storage(value, 'mol'), 'mmol')
                contents.append(
                    f"{substance}: {round(value, config.external_precision)} {unit}")

        max_volume = ('/' + str(Unit.convert_from_storage(self.max_volume, 'mL'))) \
            if self.max_volume != float('inf') else ''
        return f"Container ({self.name}) ({Unit.convert_from_storage(self.volume, 'mL')}" + \
            f"{max_volume} mL of ({contents})"

    @cache
    def has_liquid(self):
        """
        Returns: True if any substance in the container is a liquid.
        """
        return any(substance.is_liquid() for substance in self.contents)

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
    def transfer(source: Container | Plate | PlateSlicer, destination: Container, quantity: str):
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

    def get_concentration(self, solute, units='M'):
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

        numerator = Unit.convert(solute, f"{self.contents.get(solute, 0)} {config.moles_prefix}", units[0])
        if units[1].endswith('L'):
            denominator = Unit.convert_from_storage(self.volume, units[1])
        else:
            denominator = sum(
                Unit.convert(substance, f"{amount} {config.moles_prefix}", units[1]) for substance, amount in
                self.contents.items())

        return round(numerator / denominator / mult, config.external_precision)

    @staticmethod
    def create_solution(solute, solvent, name=None, **kwargs):
        """
        Create a solution.

        Two out of concentration, quantity, and total_quantity must be specified.

        Arguments:
            solute: What to dissolve.
            solvent: What to dissolve with.
            name: Optional name for new container.
            concentration: Desired concentration. ('1 M', '0.1 umol/10 uL', etc.)
            quantity: Desired quantity of solute. ('3 mL', '10 g')
            total_quantity: Desired total quantity. ('3 mL', '10 g')


        Returns:
            New container with desired solution.
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

        if 'concentration' in kwargs and 'total_quantity' in kwargs:
            concentration = kwargs['concentration']
            total_quantity = kwargs['total_quantity']
            quantity, quantity_unit = Unit.parse_quantity(total_quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be positive.")

            ratio, numerator, denominator = Unit.calculate_concentration_ratio(solute, concentration, solvent)

            if ratio <= 0:
                raise ValueError("Solution is impossible to create.")

            if numerator == 'U':
                if not solute.is_enzyme():
                    raise TypeError("Solute must be an enzyme.")
                solvent_quantity = Unit.convert(solvent, f"{quantity} {quantity_unit}", config.moles_prefix)
                units = ratio * solvent_quantity
                return Container(name,
                                 initial_contents=((solute, f"{units} U"), (solvent, f"{quantity} {quantity_unit}")))

            if quantity_unit == 'g':
                ratio *= solute.mol_weight / solvent.mol_weight
            elif quantity_unit == 'mol':
                pass
            elif quantity_unit == 'L':
                ratio *= (solute.mol_weight / solute.density) / (solvent.mol_weight / solvent.density)
            else:
                raise ValueError("Invalid quantity unit.")

            # x is quantity of solute in moles, y is quantity of solvent in moles

            y = quantity / (1 + ratio)
            x = quantity - y

            assert x >= 0 and y >= 0
            solution = Container(name,
                                 initial_contents=((solute, f"{x} {quantity_unit}"), (solvent, f"{y} {quantity_unit}")))
            return solution
        if 'quantity' in kwargs and 'total_quantity' in kwargs:
            result = Container(name, initial_contents=[(solute, kwargs['quantity'])])
            result = result.fill_to(solvent, kwargs['total_quantity'])
        else:  # 'quantity' and 'concentration'
            concentration = Unit.calculate_concentration_ratio(solute, kwargs['concentration'], solvent)
            quantity = Unit.convert(solute, kwargs['quantity'], concentration[1])
            result = Container(name, initial_contents=[(solute, kwargs['quantity'])])
            result._self_add(solvent, f"{quantity / concentration[0]} {concentration[1]}")
        contents = []
        for substance, value in result.contents.items():
            value, unit = Unit.convert_from_storage_to_standard_format(substance, value)
            contents.append(f"{value} {unit} of {substance.name}")
        result.instructions = "Add " + ", ".join(contents) + " to a container."
        return result

    @staticmethod
    def create_solution_from(source: Container, solute: Substance, concentration: str, solvent: Substance,
                             quantity: str, name=None):
        """
        Create a diluted solution from an existing solution.


        Arguments:
            source: Solution to dilute.
            solute: What to dissolve.
            concentration: Desired concentration. ('1 M', '0.1 umol/10 uL', etc.)
            solvent: What to dissolve with.
            quantity: Desired total quantity. ('3 mL', '10 g')
            name: Optional name for new container.

        Returns:
            Residual from the source container and a new container with desired solution.
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

        if solute not in source.contents:
            raise ValueError(f"Container does not contain {solute.name}.")

        if not name:
            name = f"solution of {solute.name} in {solvent.name}"

        new_ratio, numerator, denominator = Unit.calculate_concentration_ratio(solute, concentration, solvent)
        current_ratio = source.contents[solute] / sum(source.contents[substance] for
                                                      substance in source.contents if not substance.is_enzyme())
        if new_ratio <= 0:
            raise ValueError("Solution is impossible to create.")

        if abs(new_ratio - current_ratio) <= 1e-3:
            new_ratio = current_ratio

        if new_ratio > current_ratio:
            raise ValueError("Desired concentration is higher than current concentration.")

        potential_solution = Container.create_solution(solute, solvent, concentration=concentration,
                                                       total_quantity=quantity)
        ratio = potential_solution.contents[solute] / source.contents[solute]
        solution = Container(name, max_volume=f"{source.max_volume} {config.volume_prefix}")

        residual, solution = Container.transfer(source, solution, f"{source.volume * ratio} {config.volume_prefix}")
        solution = solution.fill_to(solvent, quantity)

        contents = [(*Unit.convert_from_storage_to_standard_format(solution, solution.volume), source.name),
                    (*Unit.convert_from_storage_to_standard_format(solvent, solution.contents[solvent]), solvent.name)]
        max_volume, unit = Unit.convert_from_storage_to_standard_format(solution, solution.max_volume)
        solution.instructions = ("Add "
                                 + ", ".join(f"{value} {unit} of {substance}" for value, unit, substance in contents)
                                 + f" to a {max_volume} {unit} container.")

        return residual, solution.fill_to(solvent, quantity)

    def remove(self, what: (Substance | int) = Substance.LIQUID):
        """
        Removes substances from `Container`

        Arguments:
            what: What to remove. Can be a type of substance or a specific substance. Defaults to LIQUID.

        Returns: New Container with requested substances removed.

        """
        new_container = deepcopy(self)
        new_container.contents = {substance: value for substance, value in self.contents.items()
                                  if what not in (substance._type, substance)}
        new_container.volume = sum(Unit.convert_from(substance, value, 'U' if substance.is_enzyme() else
        config.moles_prefix, config.volume_prefix) for
                                   substance, value in new_container.contents.items())
        new_container.instructions = self.instructions
        classes = {Substance.SOLID: 'solid', Substance.LIQUID: 'liquid', Substance.ENZYME: 'enzyme'}
        if what in classes:
            new_container.instructions += f"Remove all {classes[what]}s."
        else:
            new_container.instructions += f"Remove all {what.name}s."
        return new_container

    def dilute(self, solute: Substance, concentration: str, solvent: Substance, name=None):
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
        new_volume = self.volume + Unit.convert(solvent, f"{required_umoles} umol", config.volume_prefix)

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
        needed_volume, unit = Unit.get_human_readable_unit(Unit.convert(solvent, needed_umoles, 'umol'), 'L')
        result.instructions += f"Dilute with {needed_volume} {unit} of {solvent.name}."
        return result

    def dilute_mols(self, solute: Substance, quantity_in_moles: float, solvent: Substance, volume: float, name=None):
        """
        Dilutes `solute` to achieve the desired quantity in moles and volume.

        Args:
            solute: Substance to be diluted.
            quantity_in_moles: Desired quantity of the solute in moles.
            solvent: Substance to dilute with.
            volume: Desired volume of the solution in liters.
            name: Optional name for the new container.

        Returns: A new container containing a solution with the desired quantity of `solute` and volume.
        """
        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(quantity_in_moles, (int, float)):
            raise TypeError("Quantity in moles must be a number.")
        if not isinstance(solvent, Substance):
            raise TypeError("Solvent must be a substance.")
        if not isinstance(volume, (int, float)):
            raise TypeError("Volume must be a number.")
        if name and not isinstance(name, str):
            raise TypeError("New name must be a str.")
        if solute not in self.contents:
            raise ValueError(f"Container does not contain {solute.name}.")

        new_ratio, numerator, denominator = \
            Unit.calculate_concentration_ratio_moles(solute, f"{quantity_in_moles} mol", solvent)
        if numerator == 'U':
            if not solute.is_enzyme():
                raise TypeError("Solute must be an enzyme.")

        current_ratio = self.contents[solute] / sum(
            self.contents[substance] for substance in self.contents if not substance.is_enzyme())

        if new_ratio <= 0:
            raise ValueError("Solution is impossible to create.")

        if abs(new_ratio - current_ratio) <= 1e-6:
            return deepcopy(self)

        if new_ratio > current_ratio:
            raise ValueError("Desired concentration is higher than current concentration.")

        current_umoles = Unit.convert_from_storage(self.contents[solvent], 'umol')
        required_umoles = Unit.convert_from_storage(self.contents[solute], 'umol') / new_ratio - current_umoles
        new_volume = self.volume + Unit.convert(solvent, f"{required_umoles} umol", config.volume_prefix)

        if new_volume > self.max_volume:
            raise ValueError("Dilute solution will not fit in the container.")

        if name:
            # Note: this copies the container twice
            destination = deepcopy(self)
            destination.name = name
        else:
            destination = self
        result = destination._add(solvent, f"{required_umoles} umol")
        needed_volume, unit = Unit.get_human_readable_unit(Unit.convert(solvent, f"{required_umoles} umol", 'umol'),
                                                           'L')
        result.instructions += f"Dilute with {needed_volume} {unit} of {solvent.name}."
        return result

    def fill_to(self, solvent: Substance, quantity: str):
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

        current_quantity = sum(Unit.convert(substance, f"{value} {config.moles_prefix}", quantity_unit)
                               for substance, value in self.contents.items() if not substance.is_enzyme())

        required_quantity = quantity - current_quantity
        result = self._add(solvent, f"{required_quantity} {quantity_unit}")
        required_volume = Unit.convert(solvent, f"{required_quantity} {quantity_unit}", 'L')
        required_volume, unit = Unit.get_human_readable_unit(required_volume, 'L')
        result.instructions += f"Fill with {required_volume} {unit} of {solvent.name}."
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

    def volumes(self, substance: (Substance | Iterable[Substance]) = None, unit: str = None) -> numpy.ndarray:
        """

        Arguments:
            unit: unit to return volumes in.
            substance: (optional) Substance to display volumes of.

        Returns:
            numpy.ndarray of volumes for each well in desired unit.

        """

        # Arguments are type checked in PlateSlicer.volumes
        return self[:].volumes(substance=substance, unit=unit)

    def substances(self):
        """

        Returns: A set of substances present in the slice.

        """
        return self[:].substances()

    def moles(self, substance: (Substance | Iterable[Substance]), unit: str = None) -> numpy.ndarray:
        """

        Arguments:
            unit: unit to return moles in. ('mol', 'mmol', 'umol', etc.)
            substance: Substance to display moles of.

        Returns: moles of substance in each well.
        """

        # Arguments are type checked in PlateSlicer.moles
        return self[:].moles(substance=substance, unit=unit)

    def dataframe(self, unit: str, substance: (str | Substance | Iterable[Substance]) = 'all', cmap: str = None):
        """

        Arguments:
            unit: unit to return quantities in.
            substance: (optional) Substance or Substances to display quantity of.
            cmap: Colormap to shade dataframe with.

        Returns: Shaded dataframe of quantities in each well.

        """
        # Types are checked in PlateSlicer.dataframe
        return self[:].dataframe(substance=substance, unit=unit, cmap=cmap)

    def volume(self, unit: str = 'uL'):
        """
        Arguments:
            unit: unit to return volumes in.

        Returns: total volume stored in slice in uL.
        """
        return self.volumes(unit=unit).sum()

    @staticmethod
    def transfer(source: Container | Plate | PlateSlicer, destination: Plate | PlateSlicer, quantity: str):
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

    def remove(self, what=Substance.LIQUID):
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
    def __init__(self, operator, frm, to, *operands):
        self.objects_used = set()
        self.operator = operator
        self.frm: list[Container | PlateSlicer | Plate | None] = [frm]
        self.to: list[Container | PlateSlicer | Plate] = [to]
        self.trash = {}
        self.operands = operands

    def visualize(self, what, mode, unit, substance='all', cmap=None):
        """

        Provide visualization of what happened during the step.

        Args:
            what: 'source', 'destination', or 'both'
            mode: 'delta', or 'final'
            unit: Unit we are interested in. ('mmol', 'uL', 'mg')
            substance: Substance we are interested in. ('all', 'water', 'ATP')
            cmap: Colormap to use. Defaults to default_colormap from config.

        Returns: A dataframe with the requested information or a list of dataframes if what is 'both'.
        """

        def helper(elem):
            """ Returns volume of elem. """
            if substance == 'all':
                total = 0
                for subs, amount in elem.contents.items():
                    if subs.is_enzyme():
                        total += Unit.convert(subs, f"{amount} U", unit)
                    else:
                        total += Unit.convert(subs, f"{amount} {config.moles_prefix}", unit)
                return total
            assert isinstance(substance, Substance)
            if substance in elem.contents:
                quantity = f"{elem.contents[substance]} {config.moles_prefix if not substance.is_enzyme() else 'U'}"
                return Unit.convert(substance, quantity, unit)
            return 0

        if what == 'both':
            return [self.visualize('source', mode, unit), self.visualize('destination', mode, unit)]
        if what == 'source':
            what = self.frm
        elif what == 'destination':
            what = self.to
        else:
            raise ValueError("What must be source, destination, or both.")

        assert mode == 'delta' or mode == 'final'

        if not isinstance(what[0], Plate):
            return None
        data = numpy.vectorize(helper, cache=True, otypes='d')(what[1].wells)
        if mode == 'delta':
            data -= numpy.vectorize(helper, cache=True, otypes='d')(what[0].wells)
            if cmap is None:
                cmap = config.default_diverging_colormap
        if cmap is None:
            cmap = config.default_colormap
        dataframe = pandas.DataFrame(data, columns=what[0].column_names, index=what[0].row_names)
        extreme = max(abs(numpy.min(data)), abs(numpy.max(data)))
        return dataframe.style.format('{:.3f}').background_gradient(cmap, vmin=-extreme,
                                                                    vmax=extreme).set_caption(
            (substance.name if isinstance(substance, Substance) else substance) + f"  ({unit})")


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
        results (list): A dictionary used in bake to return the mutated objects.
    """

    def __init__(self):
        self.results = {}
        self.all_volume_tracking: dict[Container | PlateSlicer | Plate, dict] = {}
        self.dispensing_volume_tracking: dict[Container | PlateSlicer, dict] = {}
        self.all_substance_tracking: dict[Substance, float] = defaultdict(float)
        self.dispensing_substance_tracking: dict[Substance, float] = defaultdict(float)
        self.steps: list[RecipeStep] = []
        self.stages: dict[str, slice] = {'all': slice(None, None)}
        self.current_stage = 'all'
        self.current_stage_start = 0
        self.locked = False
        self.used = set()

    def start_stage(self, name: str):
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

    def end_stage(self, name: str):
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

    def _update_volume_dict(self, container: Container | Plate, timeframe: str, direction: str, value: str,
                            index: tuple[int, int] | None = None):
        """
        Update the volume tracking dictionary for a container or plate.

        Args:
            container: Container or PlateSlicer to update.
            timeframe: 'in' or 'out' to indicate whether volume is being added or removed.

        """
        container_name = container.name
        if isinstance(container, PlateSlicer):
            if timeframe == "dispensing":
                if container_name not in self.dispensing_volume_tracking:
                    self.dispensing_volume_tracking[container_name] = {
                        'in': np.zeros((container.n_rows, container.n_cols)),
                        'out': np.zeros((container.n_rows, container.n_cols))
                    }
                parsed_tuple = Unit.parse_quantity(value)
                self.dispensing_volume_tracking[container_name][direction][index] += Unit.convert_to_storage(
                    parsed_tuple[0], parsed_tuple[1])
            elif timeframe == "all":
                if container_name not in self.all_volume_tracking:
                    self.all_volume_tracking[container_name] = {
                        'in': np.zeros((container.n_rows, container.n_cols)),
                        'out': np.zeros((container.n_rows, container.n_cols))
                    }
                parsed_tuple = Unit.parse_quantity(value)
                self.all_volume_tracking[container_name][direction][index] += Unit.convert_to_storage(parsed_tuple[0],
                                                                                                      parsed_tuple[1])
            else:
                raise ValueError("Invalid mode.")
        else:
            if timeframe == "dispensing":
                if container_name not in self.dispensing_volume_tracking:
                    self.dispensing_volume_tracking[container_name] = {'in': 0, 'out': 0}
                parsed_tuple = Unit.parse_quantity(value)
                self.dispensing_volume_tracking[container_name][direction] += Unit.convert_to_storage(parsed_tuple[0],
                                                                                                      parsed_tuple[1])
            elif timeframe == "all":
                if container_name not in self.all_volume_tracking:
                    self.all_volume_tracking[container_name] = {'in': 0, 'out': 0}
                parsed_tuple = Unit.parse_quantity(value)
                self.all_volume_tracking[container_name][direction] += Unit.convert_to_storage(parsed_tuple[0],
                                                                                               parsed_tuple[1])
            else:
                raise ValueError("Invalid mode.")

    def uses(self, *args) -> Recipe:
        """
        Declare *containers (iterable of Containers) as being used in the recipe.
        """
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        for arg in args:
            if isinstance(arg, (Container, Plate)):
                if isinstance(arg, Plate):
                    for index, well in numpy.ndenumerate(arg.wells):
                        for substance, amount in well.contents.items():
                            self.all_substance_tracking[substance] += amount
                    for index, well in numpy.ndenumerate(arg.wells):
                        self._update_volume_dict(arg, "all", "in", f'{well.volume} {config.default_volume_unit}', index)
                else:
                    for substance, amount in arg.contents.items():
                        self.all_substance_tracking[substance] += amount
                if arg.name not in self.results:
                    self.results[arg.name] = deepcopy(arg)
                else:
                    raise ValueError(f"An object with the name: \"{arg.name}\" is already in use.")
            elif isinstance(arg, Iterable):
                unpacked = list(arg)
                if not all(isinstance(elem, (Container, Plate)) for elem in unpacked):
                    raise TypeError("Invalid type in iterable.")
                self.uses(*unpacked)
        return self

    def transfer(self, source: Container, destination: Container | Plate | PlateSlicer, quantity: str):
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
        self.steps.append(RecipeStep('transfer', source, destination, quantity))

    def create_container(self, name: str, max_volume: str = 'inf L',
                         initial_contents: Iterable[tuple[Substance, str]] | None = None):

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
        self.steps.append(RecipeStep('create_container', None, new_container, max_volume, initial_contents))

        return new_container

    def create_solution(self, solute, solvent, name=None, **kwargs):
        """
        Adds a step to the recipe which creates a solution.

        Two out of concentration, quantity, and total_quantity must be specified.

        Arguments:
            solute: What to dissolve.
            solvent: What to dissolve with.
            name: Optional name for new container.
            concentration: Desired concentration. ('1 M', '0.1 umol/10 uL', etc.)
            quantity: Desired quantity of solute. ('3 mL', '10 g')
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
        self.steps.append(RecipeStep('solution', None, new_container, solute, solvent, kwargs))

        return new_container

    def create_solution_from(self, source: Container, solute: Substance, concentration: str, solvent: Substance,
                             quantity: str, name=None):
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

        new_container = Container(name, max_volume=f"{source.max_volume} {config.volume_prefix}")
        self.uses(new_container)
        self.steps.append(RecipeStep('solution_from', source, new_container, solute, concentration, solvent, quantity))

        return new_container

    def remove(self, destination: Container | Plate | PlateSlicer, what=Substance.LIQUID):
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

        self.steps.append(RecipeStep('remove', None, destination, what))

    def dilute(self, destination: Container, solute: Substance,
               concentration: str, solvent: Substance, new_name=None):
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

        self.steps.append(RecipeStep('dilute', None, destination, solute, concentration, solvent, new_name))

    def fill_to(self, destination: Container, solvent: Substance, quantity: str):
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

        self.steps.append(RecipeStep('fill_to', None, destination, solvent, quantity))

    def bake(self):
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

        # for operation, *rest in self.steps:
        for step in self.steps:
            # Keep track of what was used in each step
            for elem in step.frm + step.to:
                if isinstance(elem, PlateSlicer):
                    step.objects_used.add(elem.plate.name)
                elif isinstance(elem, (Container, Plate)):
                    step.objects_used.add(elem.name)

            operator = step.operator
            if operator == 'create_container':
                dest = step.to[0]
                dest_name = dest.name
                step.frm.append(None)
                max_volume, initial_contents = step.operands
                step.to[0] = self.results[dest.name]
                self.used.add(dest.name)
                self.results[dest.name] = Container(dest.name, max_volume, initial_contents)
                step.to.append(self.results[dest.name])

                if isinstance(self.results[dest_name], PlateSlicer):
                    for well in self.results[dest_name].array:
                        for substance, amount in well.contents.items():
                            self.all_substance_tracking[substance] += amount

                    self.all_volume_tracking[dest]["in"] = np.full(self.results[dest_name].array.shape,
                                                                   self.results[dest_name].volume)
                elif isinstance(self.results[dest_name], Container):
                    for substance, amount in self.results[dest_name].contents.items():
                        self.all_substance_tracking[substance] += amount
                        self.all_volume_tracking[dest] = {
                            "in": dest.volume,
                            "out": 0
                        }
            elif operator == 'transfer':
                source = step.frm[0]
                source_name = source.plate.name if isinstance(source, PlateSlicer) else source.name
                dest = step.to[0]
                dest_name = dest.plate.name if isinstance(dest, PlateSlicer) else dest.name
                quantity, = step.operands

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

                # if isinstance(orig_source, PlateSlicer):
                #     for index, well in np.ndenumerate(orig_source.array):
                #         for substance, amount in well.contents.items():
                #             difference = amount - source.wells[index].contents[substance]
                #             self.dispensing_substance_tracking[substance] += difference
                #         self._update_volume_dict(self.results[source_name], "dispensing", "out", f"{quantity}", index)
                # elif isinstance(orig_source, Container):
                #     for substance, amount in orig_source.contents.items():
                #         difference = amount - source.contents[substance]
                #         self.dispensing_substance_tracking[substance] += difference
                #     self._update_volume_dict(self.results[source_name], "dispensing", "out", f"{quantity}")

                step.frm.append(self.results[source_name])
                step.to.append(self.results[dest_name])
            elif operator == 'solution':
                dest = step.to[0]
                dest_name = dest.name
                step.frm.append(None)
                solute, solvent, kwargs = step.operands

                step.to[0] = self.results[dest_name]
                self.used.add(dest_name)
                self.results[dest_name] = Container.create_solution(solute, solvent, dest_name, **kwargs)
                step.to.append(self.results[dest_name])
                if isinstance(self.results[dest_name], PlateSlicer):
                    for index, well in np.ndenumerate(self.results[dest_name].array):
                        for substance, amount in well.contents.items():
                            self.all_substance_tracking[substance] += amount
                        self._update_volume_dict(self.results[dest_name], "all", "in",
                                                 f'{self.results[dest_name].volume} {config.default_volume_unit}',
                                                 index)
                elif isinstance(self.results[dest_name], Container):
                    for substance, amount in self.results[dest_name].contents.items():
                        self.all_substance_tracking[substance] += amount
                    self._update_volume_dict(self.results[dest_name], "all", "in",
                                             f'{self.results[dest_name].volume} {config.default_volume_unit}')
            elif operator == 'solution_from':
                source = step.frm[0]
                source_name = source.name
                dest = step.to[0]
                dest_name = dest.name
                solute, concentration, solvent, quantity = step.operands
                step.frm[0] = self.results[source_name]
                step.to[0] = self.results[dest_name]

                self.used.add(source_name)
                self.used.add(dest_name)
                source = self.results[source_name]
                self.results[source_name], self.results[dest_name] = \
                    Container.create_solution_from(source, solute, concentration, solvent, quantity, dest.name)
                step.frm.append(self.results[source_name])
                step.to.append(self.results[dest_name])
                if isinstance(self.results[dest_name], Container):
                    self.all_substance_tracking[solvent] += self.results[dest_name].contents[
                                                                solvent] - dest.contents.get(solvent, 0)
                    for substance, amount in self.results[dest_name].contents.items():
                        difference = amount - self.results[source_name].contents[substance]
                        if substance != solvent:
                            self.dispensing_substance_tracking[substance] += difference
                    volume_difference_after_transfer = self.results[dest_name].volume - dest.volume
                    self._update_volume_dict(self.results[dest_name], "dispensing", "in",
                                             f"{volume_difference_after_transfer} {config.default_volume_unit}")
                    self._update_volume_dict(self.results[dest_name], "dispensing", "out",
                                             f"{volume_difference_after_transfer} {config.default_volume_unit}")
                    solvent_volume_difference = (
                            Unit.convert(solvent, f"{self.results[dest_name].contents[solvent]} {config.moles_prefix}",
                                         f'{config.default_volume_unit}')
                            - Unit.convert(solvent, f"{dest.contents.get(solvent, 0)} {config.moles_prefix}",
                                           f'{config.default_volume_unit}')
                    )
                    self._update_volume_dict(self.results[dest_name], "all", "in",
                                             f"{solvent_volume_difference} {config.default_volume_unit}")
                elif isinstance(self.results[dest_name], PlateSlicer):
                    raise ValueError("Not currently supported.")
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

                self.results[dest_name] = dest.remove(what)
                # get difference of each substance form result and dest
                if isinstance(self.results[dest_name], PlateSlicer):
                    for index, well in numpy.ndenumerate(self.results[dest_name].array):
                        volume_difference = dest.volume - self.results[dest_name].volume
                        self._update_volume_dict(self.results[dest_name], "dispensing", "out",
                                                 f'{volume_difference} {config.default_volume_unit}', index)
                elif isinstance(self.results[dest_name], Container):
                    volume_difference = dest.volume - self.results[dest_name].volume
                    self._update_volume_dict(self.results[dest_name], "dispensing", "out",
                                             f'{volume_difference} {config.default_volume_unit}')
                step.to.append(self.results[dest_name])
            elif operator == 'dilute':
                dest = step.to[0]
                dest_name = dest.name
                solute, concentration, solvent, new_name = step.operands
                step.frm.append(None)
                step.to[0] = self.results[dest_name]
                self.used.add(dest_name)
                self.results[dest_name] = self.results[dest_name].dilute(solute, concentration, solvent, new_name)
                step.to.append(self.results[dest_name])
                if isinstance(self.results[dest_name], PlateSlicer):
                    for index, well in np.ndenumerate(self.results[dest_name].array):
                        solvent_used = self.results[dest_name][index].contents[solvent] - dest[index].contents[solvent]
                        self.all_substance_tracking[solvent] += solvent_used
                        solvent_used_volume = Unit.convert(solvent, f"{solvent_used} {config.moles_prefix}",
                                                           f'{config.default_volume_unit}')
                        self._update_volume_dict(self.results[dest_name], "all", "in",
                                                 f"{solvent_used_volume} {config.default_volume_unit}", index)
                elif isinstance(self.results[dest_name], Container):
                    solvent_used = self.results[dest_name].contents[solvent] - dest.contents.get(solvent, 0)
                    self.all_substance_tracking[solvent] += solvent_used
                    solvent_used_volume = Unit.convert(solvent, f"{solvent_used} {config.moles_prefix}",
                                                       f'{config.default_volume_unit}')
                    self._update_volume_dict(self.results[dest_name], "all", "in",
                                             f"{solvent_used_volume} {config.default_volume_unit}")
            elif operator == 'fill_to':
                dest = step.to[0]
                dest_name = dest.plate.name if isinstance(dest, PlateSlicer) else dest.name
                solvent, quantity = step.operands
                step.frm.append(None)
                step.to[0] = self.results[dest_name]
                self.used.add(dest_name)

                if isinstance(dest, PlateSlicer):
                    dest = deepcopy(dest)
                    dest.plate = self.results[dest_name]
                else:
                    dest = self.results[dest_name]

                self.results[dest_name] = dest.fill_to(solvent, quantity)
                step.substances_used.add(solvent)
                if isinstance(self.results[dest_name], PlateSlicer):
                    for index, well in np.ndenumerate(self.results[dest_name].array):
                        solvent_used = self.results[dest_name][index].contents[solvent] - dest[index].contents.get(
                            solvent, 0)
                        self.all_substance_tracking[solvent] += solvent_used
                        solvent_used_volume = Unit.convert(solvent, f"{solvent_used} {config.moles_prefix}",
                                                           f'{config.default_volume_unit}')
                        self._update_volume_dict(self.results[dest_name], "all", "in",
                                                 f"{solvent_used_volume} {config.default_volume_unit}", index)
                elif isinstance(self.results[dest_name], Container):
                    solvent_used = self.results[dest_name].contents[solvent] - dest.contents.get(solvent, 0)
                    self.all_substance_tracking[solvent] += solvent_used
                    solvent_used_volume = Unit.convert(solvent, f"{solvent_used} {config.moles_prefix}",
                                                       f'{config.default_volume_unit}')
                    self._update_volume_dict(self.results[dest_name], "all", "in",
                                             f"{solvent_used_volume} {config.default_volume_unit}")
                step.to.append(self.results[dest_name])

        if len(self.used) != len(self.results):
            raise ValueError("Something declared as used wasn't used.")
        self.locked = True
        return self.results

    def _dry_bake(self, step_list: list[RecipeStep], tracking_dict: dict[Substance, float], dest_containers: list[str]):
        for step in step_list:
            operator = step.operator
            if operator == 'create_container':
                if step.to[1].name in dest_containers:
                    if isinstance(step.to[1], PlateSlicer):
                        for well in step.to[1].array:
                            for substance, amount in well.contents.items():
                                tracking_dict[substance] += amount
                    elif isinstance(step.to[1], Container):
                        for substance, amount in step.to[1].contents.items():
                            tracking_dict[substance] += amount
            elif operator == 'transfer':
                if step.to[1].name in dest_containers:
                    if isinstance(step.frm[0], PlateSlicer):
                        for index, well in np.ndenumerate(step.frm[0].array):
                            for substance, amount in well.contents.items():
                                difference = step.frm[0].wells[index].contents.get(substance, 0) - step.frm[1].wells[
                                    index].contents.get(substance, 0)
                                tracking_dict[substance] += difference
                    elif isinstance(step.frm[0], Container):
                        for substance, amount in step.frm[0].contents.items():
                            difference = step.frm[0].contents.get(substance, 0) - step.frm[1].contents.get(substance, 0)
                            tracking_dict[substance] += difference
                elif step.frm[1].name in dest_containers:
                    if isinstance(step.frm[0], PlateSlicer):
                        for index, well in np.ndenumerate(step.frm[0].array):
                            for substance, amount in well.contents.items():
                                difference = step.frm[1].wells[index].contents.get(substance, 0) - step.frm[0].wells[
                                    index].contents.get(substance, 0)
                                tracking_dict[substance] += difference
                    elif isinstance(step.frm[0], Container):
                        for substance, amount in step.frm[0].contents.items():
                            difference = step.frm[1].contents.get(substance, 0) - step.frm[0].contents.get(substance, 0)
                            tracking_dict[substance] += difference
            elif operator == 'solution':
                if step.to[1].name in dest_containers:
                    if isinstance(step.to[1], PlateSlicer):
                        for index, well in np.ndenumerate(step.to[1].array):
                            for substance, amount in well.contents.items():
                                tracking_dict[substance] += amount
                    elif isinstance(step.to[1], Container):
                        for substance, amount in step.to[1].contents.items():
                            tracking_dict[substance] += amount
            elif operator == 'solution_from':
                solute, concentration, solvent, quantity = step.operands
                if step.to[1].name in dest_containers:
                    if isinstance(step.to[1], Container):
                        tracking_dict[solvent] += step.to[1].contents[solvent] - step.to[0].contents.get(solvent, 0)
                        for substance, amount in step.to[1].contents.items():
                            difference = amount - step.frm[0].contents[substance]
                            if substance != solvent:
                                tracking_dict[substance] += difference
                    elif isinstance(step.to[1], PlateSlicer):
                        raise ValueError("Not currently supported.")
            elif operator == 'remove':
                what, = step.operands
                if isinstance(step.to[0], PlateSlicer):
                    for index, well in numpy.ndenumerate(step.to[0].array):
                        removed = well.contents[what]
                        # TODO: add to special trash
                elif isinstance(step.to[0], Container):
                    removed = step.to[0].contents[what]
                    # TODO: add to special trash
            elif operator == 'dilute':
                solute, concentration, solvent, new_name = step.operands
                if step.to[0].name in dest_containers:
                    if isinstance(step.to[1], PlateSlicer):
                        for index, well in np.ndenumerate(step.to[1].array):
                            solvent_used = step.to[1][index].contents[solvent] - \
                                           step.to[0][index].contents[solvent]
                            tracking_dict[solvent] += solvent_used
                    elif isinstance(step.to[1], Container):
                        solvent_used = step.to[1].contents[solvent] - step.to[0].contents.get(solvent, 0)
                        tracking_dict[solvent] += solvent_used
            elif operator == 'fill_to':
                solvent, quantity = step.operands
                if step.to[0].name in dest_containers:
                    if isinstance(step.to[1], PlateSlicer):
                        for index, well in np.ndenumerate(step.to[1].array):
                            solvent_used = step.to[1].contents[solvent] - step.to[0][
                                index].contents.get(
                                solvent, 0)
                            tracking_dict[solvent] += solvent_used
                    elif isinstance(step.to[1], Container):
                        solvent_used = step.to[1].contents[solvent] - step.to[0].contents.get(solvent, 0)
                        tracking_dict[solvent] += solvent_used
        return tracking_dict

    def amount_used(self, substance: Substance, timeframe: str = 'all', unit: str = None,
                    destinations: Iterable[Container | Plate] | str = "plates"):
        """
        Returns the amount of substance used in the recipe.

        Args:
            substance: Substance to check.
            timeframe: 'before' or 'during'. Before refers to the initial state of the containers aka recipe "prep", and
            during refers to
            unit: Unit to return amount in.

        Returns: Amount of substance used in the recipe.

        """
        if unit is None:
            unit = 'U' if substance.is_enzyme() else config.default_moles_unit

        from_unit = 'U' if substance.is_enzyme() else config.moles_prefix

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
            raise ValueError("Invalid Timeframe")

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
            elif step.frm[0] is not None and step.frm[0].name in dest_names:
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
                f"Destination containers contains {delta} {from_unit} less of substance: {substance}" +
                " after stage {timeframe}. Did you specify the correct destinations?")
        return Unit.convert(substance, f'{delta} {from_unit}', unit)

    def substances_used(self, timeframe: str = 'before'):
        """
        Returns the set of substances used in the recipe.

        Returns: Set of substances used in the recipe.

        """
        if timeframe == 'all':
            return set(self.all_substance_tracking.keys())
        elif timeframe == 'dispensing':
            return set(self.dispensing_substance_tracking.keys())

    def volume_used(self, container: Container, timeframe: str = 'during', unit: str = None):
        # TODO: output with external precision rounding
        """
        Returns the volume used of a container in the recipe.

        Args:
            container: Container to check.
            timeframe: 'before' or 'during'. Before refers to the initial state of the containers aka recipe "prep", and
            during refers to
            unit: Unit to return volume in.

        Returns: Volume used of container in the recipe.
        """
        if unit is None:
            unit = config.default_volume_unit
        if timeframe == 'all':
            output_dict = deepcopy(self.all_volume_tracking[container.name])
        elif timeframe == 'dispensing':
            output_dict = deepcopy(self.dispensing_volume_tracking[container.name])
        else:
            raise ValueError("Invalid timeframe.")
        output_dict['in'] = round(Unit.convert_from_storage(output_dict['in'], unit), config.external_precision)
        output_dict['out'] = round(Unit.convert_from_storage(output_dict['out'], unit), config.external_precision)
        return output_dict

    def visualize(self, what: Plate, mode: str, when: (int | str), unit: str,
                  substance: (str | Substance) = 'all', cmap: str = None):
        """

        Provide visualization of what happened during the step.

        Args:
            what: Plate we are interested in.
            mode: 'delta', or 'final'
            when: Number of the step or the name of the stage to visualize.
            unit: Unit we are interested in. ('mmol', 'uL', 'mg')
            substance: Substance we are interested in. ('all', water, ATP)
            cmap: Colormap to use. Defaults to default_colormap from config.

        Returns: A dataframe with the requested information.
        """
        if not isinstance(what, Plate):
            raise TypeError("What must be a Plate.")
        if mode not in ['delta', 'final']:
            raise ValueError("Invalid mode.")
        if not isinstance(when, (int, str)):
            raise TypeError("When must be an int or str.")
        if isinstance(when, str) and when not in self.stages:
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
                    substance_unit = 'U' if subst.is_enzyme() else config.moles_prefix
                    amount += Unit.convert_from(subst, quantity, substance_unit, unit)
                return amount
            else:
                substance_unit = 'U' if substance.is_enzyme() else config.moles_prefix
                return Unit.convert_from(substance, elem.contents.get(substance, 0), substance_unit, unit)

        if isinstance(when, str):
            start_index = self.stages[when].start
            end_index = self.stages[when].stop
        else:
            if when >= len(self.steps):
                raise ValueError("Invalid step number.")
            if when < 0:
                when = max(0, len(self.steps) + when)
            start_index = when
            end_index = when + 1

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
            raise ValueError("Plate not used in the desired step(s).")

        df = None
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
        vmin, vmax = df.min().min(), df.max().max()
        styler = df.style.format(precision=precision).background_gradient(cmap, vmin=vmin, vmax=vmax)
        return styler


class PlateSlicer(Slicer):
    """ @private """

    def __init__(self, plate, item):
        self.plate = plate
        super().__init__(plate.wells, plate.row_names, plate.column_names, item)

    @property
    def array(self):
        """ @private """
        return self.plate.wells

    @array.setter
    def array(self, array):
        self.plate.wells = array

    def get_dataframe(self):
        return pandas.DataFrame(self.plate.wells, columns=self.plate.column_names,
                                index=self.plate.row_names).iloc[self.slices]

    @staticmethod
    def _add(frm, to, quantity):
        to = copy(to)
        to.plate = deepcopy(to.plate)
        to.apply(lambda elem: elem._add(frm, quantity))
        return to.plate

    @staticmethod
    def _transfer(frm, to, quantity):
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

    def dataframe(self, unit: str, substance: (str | Substance | Iterable[Substance]) = 'all', cmap: str = None):
        """

        Arguments:
            unit: unit to return quantities in.
            substance: Substance or Substances to display quantity of.
            cmap: Colormap to shade dataframe with.

        Returns: Shaded dataframe of quantities in each well.

        """
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")
        if (substance != 'all' and not isinstance(substance, Substance) and
                not (isinstance(substance, Iterable) and all(isinstance(x, Substance) for x in substance))):
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
                    substance_unit = 'U' if subst.is_enzyme() else config.moles_prefix
                    amount += Unit.convert_from(subst, quantity, substance_unit, unit)
                return amount
            elif isinstance(substance, Iterable):
                amount = 0
                for subst in substance:
                    substance_unit = 'U' if subst.is_enzyme() else config.moles_prefix
                    amount += Unit.convert_from(subst, elem.contents.get(subst, 0), substance_unit, unit)
                return amount
            else:
                substance_unit = 'U' if substance.is_enzyme() else config.moles_prefix
                return Unit.convert_from(substance, elem.contents.get(substance, 0), substance_unit, unit)

        values = numpy.vectorize(helper, cache=True, otypes='d')(self.get())
        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        df = self.get_dataframe().apply(numpy.vectorize(helper, cache=True, otypes='d'))
        vmin, vmax = df.min().min(), df.max().max()
        styler = df.style.format(precision=precision).background_gradient(cmap, vmin=vmin, vmax=vmax)
        return styler

    def volumes(self, substance: (Substance | Iterable[Substance]) = None, unit: str = None) -> numpy.ndarray:
        """

        Arguments:
            unit:  unit to return volumes in.
            substance: (optional) Substance to display volumes of.

        Returns:
            numpy.ndarray of volumes for each well in uL

        """
        if unit is None:
            unit = config.default_volume_unit

        if substance is None:
            return numpy.vectorize(lambda elem: Unit.convert_from_storage(elem.volume, unit), cache=True,
                                   otypes='d')(self.get())

        if isinstance(substance, Substance):
            substance = [substance]

        if not (substance is None or
                (isinstance(substance, Iterable) and all(isinstance(x, Substance) for x in substance))):
            raise TypeError("Substance must be a Substance or an Iterable of Substances.")
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")

        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']

        def helper(elem):
            amount = 0
            """ Returns volume of elem. """
            if substance is None:
                for subs, quantity in elem.contents.items():
                    substance_unit = 'U' if subs.is_enzyme() else config.moles_prefix
                    amount += Unit.convert_from(subs, quantity, substance_unit, unit)
            else:
                for subs in substance:
                    substance_unit = 'U' if subs.is_enzyme() else config.moles_prefix
                    amount += Unit.convert_from(subs, elem.contents.get(subs, 0), substance_unit, unit)
            return round(amount, precision)

        return numpy.vectorize(helper, cache=True, otypes='d')(self.get())

    def substances(self):
        """

        Returns: A set of substances present in the plate.

        """
        substances_arr = numpy.vectorize(lambda elem: elem.contents.keys(), cache=True)(self.get())
        return set.union(*map(set, substances_arr.flatten()))

    def moles(self, substance: (Substance | Iterable[Substance]), unit: str = 'mol') -> numpy.ndarray:
        """
        Arguments:
            unit: unit to return moles in. ('mol', 'mmol', 'umol', etc.)
            substance: Substance to display moles of.

        Returns: moles of substance in each well.
        """

        if isinstance(substance, Substance):
            substance = [substance]
        if unit is None:
            unit = config.default_moles_unit

        if not isinstance(substance, Iterable) or not all(isinstance(x, Substance) for x in substance):
            raise TypeError(f"Substance must be a Substance or an Iterable of Substances.")
        if not isinstance(unit, str):
            raise TypeError(f"Unit must be a str.")

        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']

        def helper(elem):
            amount = 0
            for subs in substance:
                if not subs.is_enzyme():
                    amount += Unit.convert_from(subs, elem.contents.get(subs, 0), config.moles_prefix, unit)
            return round(amount, precision)

        return numpy.vectorize(helper, cache=True, otypes='d')(self.get())

    def remove(self, what=Substance.LIQUID):
        """
        Removes substances from slice

        Arguments:
            what: What to remove. Can be a type of substance or a specific substance. Defaults to LIQUID.

        Returns: New Plate with requested substances removed.

        """
        self.plate = deepcopy(self.plate)
        self.apply(lambda elem: elem.remove(what))
        return self.plate

    def fill_to(self, solvent, quantity):
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
