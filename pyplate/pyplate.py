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

from typing import Tuple, Dict, Iterable
from copy import deepcopy, copy
import numpy
from pyplate.slicer import Slicer
from pyplate import config


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
        prefixes = {'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3, 'c': 1e-2, 'd': 1e-1, '': 1, 'k': 1e3, 'M': 1e6}
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

        if from_unit == 'U' and not substance.is_enzyme():
            raise ValueError("Only enzymes can be measured in activity units. 'U'")
        # if from_unit == 'L' and not substance.is_liquid():
        #     raise ValueError("Only liquids can be measured by volume. 'L'")

        for suffix in ['U', 'L', 'g', 'mol']:
            if from_unit.endswith(suffix):
                prefix = from_unit[:-len(suffix)]
                quantity *= Unit.convert_prefix_to_multiplier(prefix)
                from_unit = suffix
                break

        result = None
        if to_unit.endswith('U'):
            prefix = to_unit[:-1]
            if not substance.is_enzyme():
                return 0
            if not from_unit == 'U':
                raise ValueError("Enzymes can only be measured in activity units. 'U'")
            result = quantity
        elif to_unit.endswith('L'):
            prefix = to_unit[:-1]
            # if not substance.is_liquid():
            #     return 0
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
    def get_human_readable_unit(value: float, unit: str):
        """
        Returns a unit that makes the value more human-readable.

        Args:
            value: Value to work with.
            unit:  Unit to determine type and default unit if value is zero.

        Returns: New unit.

        """
        if value == 0:
            return unit
        value = abs(value)
        if unit[-1] == 'L':
            unit = 'L'
        elif unit[-3:] == 'mol':
            unit = 'mol'
        elif unit[-1] == 'g':
            unit = 'g'
        elif unit[-1] == 'U':
            unit = 'U'
        multiplier = 1
        while value < 1:
            value *= 1e3
            multiplier /= 1e3

        multiplier = max(multiplier, 1e-6)

        return {1: '', 1e-3: 'm', 1e-6: 'u'}[multiplier] + unit

    @staticmethod
    def calculate_concentration_ratio(solute: Substance, concentration: str, solvent: Substance):
        c, numerator, denominator = Unit.parse_concentration(concentration)
        if numerator not in ('g', 'L', 'mol'):
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
        return ratio


class Substance:
    """
    An abstract chemical or biological entity (e.g., reagent, enzyme, solvent, etc.). Immutable.
    Solids and enzymes are assumed to require zero volume.

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
        # if self.is_solid():
        #     return f"SOLID ({self.name}: {self.mol_weight})"
        # if self.is_liquid():
        #     return f"LIQUID ({self.name}: {self.mol_weight}, {self.density})"
        # return f"ENZYME ({self.name})"
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

    def _transfer(self, source_container: Container, volume: str):
        """
        Move volume ('10 mL') from container to self.

        Arguments:
            source_container: `Container` to transfer from.
            volume: How much to transfer.

        Returns: New source and destination container.
        """

        if not isinstance(source_container, Container):
            raise TypeError("Invalid source type.")
        volume_to_transfer, unit = Unit.parse_quantity(volume)
        volume_to_transfer = Unit.convert_to_storage(volume_to_transfer, 'L')
        volume_to_transfer = round(volume_to_transfer, config.internal_precision)
        if unit != 'L':
            raise ValueError("We can only transfer volumes from other containers.")
        if volume_to_transfer > source_container.volume:
            raise ValueError(f"Not enough mixture left in source container ({source_container.name}). " +
                             f"Only {Unit.convert_from_storage(source_container.volume, 'mL')} mL available, " +
                             f"{Unit.convert_from_storage(volume_to_transfer, 'mL')} mL needed.")
        # source_container, to = source_container.copy(), self.copy()
        source_container, to = deepcopy(source_container), deepcopy(self)
        ratio = volume_to_transfer / source_container.volume
        for substance, amount in source_container.contents.items():
            to.contents[substance] = round(to.contents.get(substance, 0) + amount * ratio,
                                           config.internal_precision)
            source_container.contents[substance] = round(source_container.contents[substance] - amount * ratio,
                                                         config.internal_precision)
        to.volume = round(to.volume + volume_to_transfer, config.internal_precision)
        if to.volume > to.max_volume:
            raise ValueError(f"Exceeded maximum volume in {to.name}.")
        source_container.volume = round(source_container.volume - volume_to_transfer, config.internal_precision)
        return source_container, to

    def _transfer_slice(self, source_slice: Plate or PlateSlicer, volume: str):
        """
        Move volume ('10 mL') from slice to self.

        Arguments:
            source_slice: Slice or Plate to transfer from.
            volume: How much to transfer.

        Returns:
            A new plate and a new container, both modified.
        """

        def helper_func(elem):
            """ Moves volume from elem to to_array[0]"""
            elem, to_array[0] = Container.transfer(elem, to_array[0], volume)
            return elem

        if isinstance(source_slice, Plate):
            source_slice = source_slice[:]
        if not isinstance(source_slice, PlateSlicer):
            raise TypeError("Invalid source type.")
        to = deepcopy(self)
        source_slice = copy(source_slice)
        source_slice.plate = deepcopy(source_slice.plate)
        volume_to_transfer, unit = Unit.parse_quantity(volume)
        volume_to_transfer = Unit.convert_to_storage(volume_to_transfer, 'L')
        volume_to_transfer = round(volume_to_transfer, config.internal_precision)
        if unit != 'L':
            raise ValueError("We can only transfer volumes from other containers.")

        if source_slice.size * volume_to_transfer > (to.max_volume - to.volume):
            raise ValueError(f"Exceeded maximum volume in {to.name}.")

        if source_slice.size == 1:
            result, to = Container.transfer(source_slice.get(), to, volume)
        else:
            to_array = [to]
            result = numpy.vectorize(helper_func, cache=True)(source_slice.get())
            to = to_array[0]
        source_slice.set(result)
        return source_slice.plate, to

    def __repr__(self):
        contents = []
        for substance, value in sorted(self.contents.items(), key=lambda elem: (elem[0]._type, -elem[1])):
            if substance.is_enzyme():
                contents.append(f"{substance}: {value}")
            else:
                unit = Unit.get_human_readable_unit(Unit.convert_from_storage(value, 'mol'), 'mmol')
                contents.append(
                    f"{substance}: {round(Unit.convert_from_storage(value, unit), config.external_precision)} {unit}")

        max_volume = ('/' + str(Unit.convert_from_storage(self.max_volume, 'mL'))) \
            if self.max_volume != float('inf') else ''
        return f"Container ({self.name}) ({Unit.convert_from_storage(self.volume, 'mL')}" + \
            f"{max_volume} mL of ({contents})"

    @staticmethod
    def add(source: Substance, destination: Container, quantity: str) -> Container:
        """
        Add the given quantity ('10 mol') of the source substance to the destination container.

        Arguments:
            source: Substance to add to `destination`.
            destination: Container to add to.
            quantity: How much `Substance` to add.

        Returns:
            A new copy of `destination` container.
        """
        if not isinstance(destination, Container):
            raise TypeError("You can only use Container.add to add to a Container")
        destination = deepcopy(destination)
        destination._self_add(source, quantity)
        return destination

    @staticmethod
    def transfer(source: Container | Plate | PlateSlicer, destination: Container, volume: str):
        """
        Move volume ('10 mL') from source to destination container,
        returning copies of the objects with amounts adjusted accordingly.

        Arguments:
            source: Container, plate, or slice to transfer from.
            destination: Container to transfer to:
            volume: How much to transfer.

        Returns:
            A tuple of (T, Container) where T is the type of the source.
        """
        if not isinstance(destination, Container):
            raise TypeError("You can only use Container.transfer into a Container")
        if isinstance(source, Container):
            return destination._transfer(source, volume)
        if isinstance(source, (Plate, PlateSlicer)):
            return destination._transfer_slice(source, volume)
        raise TypeError("Invalid source type.")

    @staticmethod
    def create_solution(solute: Substance, concentration: str, solvent: Substance, quantity: str, name=None):
        """
        Create a solution.


        Arguments:
            solute: What to dissolve.
            concentration: Desired concentration. ('1 M', '0.1 umol/10 uL', etc.)
            solvent: What to dissolve with.
            quantity: Desired total quantity. ('3 mL', '10 g')
            name: Optional name for new container.

        Returns:
            New container with desired solution.
        """
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

        quantity, quantity_unit = Unit.parse_quantity(quantity)
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        if not name:
            name = f"{solute.name} {concentration:.2}M"

        ratio = Unit.calculate_concentration_ratio(solute, concentration, solvent)

        if ratio <= 0:
            raise ValueError("Solution is impossible to create.")

        if quantity_unit == 'g':
            ratio *= solute.mol_weight / solvent.mol_weight
        elif quantity_unit == 'mol':
            pass
        elif quantity_unit == 'L':
            ratio *= (solute.mol_weight / solute.density) / (solvent.mol_weight / solvent.density)
        else:
            raise ValueError("Invalid quantity unit.")

        y = quantity / (1 + ratio)
        x = quantity - y

        assert x >= 0 and y >= 0
        return Container(name, initial_contents=((solute, f"{x} {quantity_unit}"), (solvent, f"{y} {quantity_unit}")))

    def remove(self, what=Substance.LIQUID):
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
        config.moles_prefix, config.volume_prefix) for substance, value in
                                   new_container.contents.items())
        return new_container

    def dilute(self, solute: Substance, concentration: str, solvent: Substance, new_name=None):
        """
        Dilutes `solute` in solution to `concentration`.

        Args:
            solute: Substance which is subject to dilution.
            concentration: Desired concentration.
            solvent: What to dilute with.
            new_name: Optional name for new container.

        Returns: A new container containing a solution with the desired concentration of `solute`.

        """
        if not isinstance(solute, Substance):
            raise TypeError("Solute must be a Substance.")
        if not isinstance(concentration, str):
            raise TypeError("Concentration must be a str.")
        if not isinstance(solvent, Substance):
            raise TypeError("Solvent must be a substance.")
        if new_name and not isinstance(new_name, str):
            raise TypeError("New name must be a str.")
        if solute not in self.contents:
            raise ValueError(f"Container does not contain {solute.name}.")

        if solute.is_enzyme():
            # TODO: Support this.
            raise ValueError("Not currently supported.")

        current_ratio = self.contents[solute] / sum(self.contents[substance] for substance in self.contents)
        new_ratio = Unit.calculate_concentration_ratio(solute, concentration, solvent)

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
            raise ValueError("Dilute solution will not fit in container.")

        if new_name:
            # Note: this copies the container twice
            destination = deepcopy(self)
            destination.name = new_name
        else:
            destination = self
        return Container.add(solvent, destination, f"{required_umoles} umol")


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

        self.wells = numpy.array([[Container(f"well {row + 1},{col + 1}",
                                             max_volume=f"{max_volume_per_well} L")
                                   for col in range(self.n_columns)] for row in range(self.n_rows)])

    def __getitem__(self, item) -> PlateSlicer:
        return PlateSlicer(self, item)

    def __repr__(self):
        return f"Plate: {self.name}"

    def volumes(self, substance: Substance = None, unit: str = 'uL') -> numpy.ndarray:
        """

        Arguments:
            unit: unit to return volumes in.
            substance: (optional) Substance to display volumes of.

        Returns:
            numpy.ndarray of volumes for each well in desired unit.

        """
        return self[:].volumes(substance=substance, unit=unit)

    def substances(self):
        """

        Returns: A set of substances present in the slice.

        """
        return self[:].substances()

    def moles(self, substance: Substance, unit: str = 'mol') -> numpy.ndarray:
        """
        Arguments:
            unit: unit to return moles in. ('mol', 'mmol', 'umol', etc.)
            substance: Substance to display moles of.

        Returns: moles of substance in each well.
        """
        return self[:].moles(substance=substance, unit=unit)

    def volume(self, unit: str = 'uL'):
        """
        Arguments:
            unit: unit to return volumes in.

        Returns: total volume stored in slice in uL.
        """
        return self.volumes(unit=unit).sum()

    @staticmethod
    def add(source: Substance, destination: Plate | PlateSlicer, quantity: str):
        """
        Add the given quantity ('10 mol') of the source substance to the destination.

        Arguments:
            source: `Substance` to add.
            destination: Plate or slice of a plate to add to.
            quantity: How much to add.
        Returns:
            A new copy of `destination` plate.
        """
        if not isinstance(destination, (Plate, PlateSlicer)):
            raise TypeError("You can only use Plate.add to add to a Plate")
        if isinstance(destination, Plate):
            destination = destination[:]
        # noinspection PyProtectedMember
        return PlateSlicer._add(source, destination, quantity)

    @staticmethod
    def transfer(source: Container | Plate | PlateSlicer, destination: Plate | PlateSlicer, volume: str):
        """
        Move volume ('10 mL') from source to destination,
        returning copies of the objects with amounts adjusted accordingly.

        Arguments:
            source: What to transfer.
            destination: Plate or slice of a plate to transfer to.
            volume: How much to transfer.

        Returns:
            A tuple of (T, Plate) where T is the type of the source.
        """
        if not isinstance(destination, (Plate, PlateSlicer)):
            raise TypeError("You can only use Plate.transfer into a Plate")
        # noinspection PyProtectedMember
        return PlateSlicer._transfer(source, destination, volume)

    def remove(self, what=Substance.LIQUID):
        """
        Removes substances from `Plate`

        Arguments:
            what: What to remove. Can be a type of substance or a specific substance. Defaults to LIQUID.

        Returns: New Plate with requested substances removed.

        """
        return self[:].remove(what)


class Recipe:
    """
    A list of instructions for transforming one set of containers into another. The intended workflow is to declare
    the source containers, enumerate the desired transformations, and call recipe.bake(). This method will ensure
    that all solid and liquid handling instructions are valid. If they are indeed valid, then the updated containers
    will be generated. Once recipe.bake() has been called, no more instructions can be added and the Recipe is
    considered immutable.

    Attributes:
        locked (boolean): Is the recipe locked from changes?
        steps (list): A list of steps to be completed upon bake() bring called.
        used (list): A list of Containers and Plates to be used in the recipe.
        results (list): A list used in bake to return the mutated objects.
        indexes (dict): A dictionary used to locate objects in the used list.
    """

    def __init__(self):
        self.indexes = {}
        self.results = []
        self.steps = []
        self.locked = False
        self.used = set()

    def uses(self, *args):
        """
        Declare *containers (iterable of Containers) as being used in the recipe.
        """
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        for arg in args:
            if arg not in self.indexes:
                # TODO: Do we need to keep track of substances?
                if isinstance(arg, (Container, Plate)):
                    self.indexes[arg] = len(self.results)
                    self.results.append(deepcopy(arg))
        return self

    def add(self, source: Substance, destination: Container | Plate | PlateSlicer, quantity: str):
        """
        Adds a step to the recipe which will move the given quantity ('10 mol')
        of the source substance to the destination.

        """
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        if not isinstance(source, Substance):
            raise TypeError("Invalid source type.")
        if not isinstance(destination, (Container, Plate, PlateSlicer)):
            raise TypeError("Invalid destination type.")
        if (destination.plate if isinstance(destination, PlateSlicer) else destination) not in self.indexes:
            name = destination.plate.name if isinstance(destination, PlateSlicer) else destination.name
            raise ValueError(f"Destination {name} has not been previously declared for use.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str. ('5 mol', '5 g')")
        if isinstance(destination, Plate):
            destination = destination[:]
        self.steps.append(('add', source, destination, quantity))
        return self

    def transfer(self, source: Container, destination: Container | Plate, volume: str):
        """
        Adds a step to the recipe which will move volume from source to destination.
        Note that all Substances in the source will be transferred in proportion to their volumetric ratios.

        """
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        if not isinstance(destination, (Container, Plate, PlateSlicer)):
            raise TypeError("Invalid destination type.")
        if not isinstance(source, (Substance, Container, PlateSlicer)):
            raise TypeError("Invalid source type.")
        if (source.plate if isinstance(source, PlateSlicer) else source) not in self.indexes:
            raise ValueError("Source not found in declared uses.")
        if (destination.plate if isinstance(destination, PlateSlicer) else destination) not in self.indexes:
            name = destination.plate.name if isinstance(destination, PlateSlicer) else destination.name
            raise ValueError(f"Destination {name} has not been previously declared for use.")
        if not isinstance(volume, str):
            raise TypeError("Volume must be a str. ('5 mL')")
        if isinstance(source, Plate):
            source = source[:]
        if isinstance(destination, Plate):
            destination = destination[:]
        self.steps.append(('transfer', source, destination, volume))
        return self

    def create_container(self, name: str, max_volume: str = 'inf L', initial_contents=None):

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
        new_container = Container(name, max_volume)
        self.uses(new_container)
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
                self.steps.append(('add', substance, new_container, quantity))
        return new_container

    def create_solution(self, solute: Substance, concentration: str,
                        solvent: Substance, quantity: str, name=None):
        """

        Adds a step to the recipe which creates a stock solution.

        Arguments:
            solute: What to dissolve.
            concentration: Desired concentration.
            solvent: What to dissolve with.
            quantity: Desired total quantity. ('10 mL')
            name: Optional name for new container.

        Returns:
            A new Container so that it may be used in later recipe steps.

        """
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        if not isinstance(solute, Substance):
            raise TypeError("What must be a Substance.")
        if not isinstance(concentration, str):
            raise TypeError("Concentration must be a str.")
        if not isinstance(solvent, Substance):
            raise TypeError("Solvent must be a Substance.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")
        if name and not isinstance(name, str):
            raise TypeError("Name must be a str.")

        if not name:
            name = f"{solute.name} {concentration}"
        ratio = Unit.calculate_concentration_ratio(solute, concentration, solvent)
        if ratio <= 0:
            raise ValueError("Solution is impossible to create.")

        new_container = Container(name)
        self.uses(new_container)
        self.steps.append(('solution', new_container, solute, concentration, solvent, quantity))
        return new_container

    def remove(self, destination: Container | Plate | PlateSlicer, what=Substance.LIQUID):
        """
        Adds a step to removes substances from destination.

        Arguments:
            destination: What to remove from.
            what: What to remove. Can be a type of substance or a specific substance. Defaults to LIQUID.
        """

        if isinstance(destination, PlateSlicer):
            if destination.plate not in self.indexes:
                raise ValueError(f"Destination {destination.plate.name} has not been previously declared for use.")
        elif isinstance(destination, (Container, Plate)):
            if destination not in self.indexes:
                raise ValueError(f"Destination {destination.name} has not been previously declared for use.")
        else:
            raise TypeError(f"Invalid destination type: {type(destination)}")

        self.steps.append(('remove', what, destination))

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
        if destination not in self.indexes:
            raise ValueError(f"Destination {destination.name} has not been previously declared for use.")
        if solute not in destination.contents:
            raise ValueError(f"Container does not contain {solute.name}.")

        ratio = Unit.calculate_concentration_ratio(solute, concentration, solvent)
        if ratio <= 0:
            raise ValueError("Concentration is impossible to create.")

        if solute.is_enzyme():
            # TODO: Support this.
            raise ValueError("Not currently supported.")

        self.steps.append(('dilute', destination, solute, concentration, solvent, new_name))

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

        for operation, *rest in self.steps:
            if operation == 'add':
                frm, dest, quantity = rest
                to_index = self.indexes[dest] if not isinstance(dest, PlateSlicer) else self.indexes[dest.plate]

                # containers and such can change while building the recipe
                if isinstance(dest, PlateSlicer):
                    new_to = deepcopy(dest)
                    new_to.plate = self.results[to_index]
                    dest = new_to
                else:
                    dest = self.results[to_index]

                if isinstance(dest, Container):
                    dest = Container.add(frm, dest, quantity)
                elif isinstance(dest, PlateSlicer):
                    dest = Plate.add(frm, dest, quantity)

                self.results[to_index] = dest
                self.used.add(to_index)
            elif operation == 'transfer':
                frm, dest, quantity = rest
                # used items can change in a recipe
                frm_index = self.indexes[frm] if not isinstance(frm, PlateSlicer) else self.indexes[frm.plate]
                to_index = self.indexes[dest] if not isinstance(dest, PlateSlicer) else self.indexes[dest.plate]

                self.used.add(frm_index)
                self.used.add(to_index)

                # containers and such can change while baking the recipe
                if isinstance(frm, PlateSlicer):
                    new_frm = deepcopy(frm)
                    new_frm.plate = self.results[frm_index]
                    frm = new_frm
                else:
                    frm = self.results[frm_index]

                if isinstance(dest, PlateSlicer):
                    new_to = deepcopy(dest)
                    new_to.plate = self.results[to_index]
                    dest = new_to
                else:
                    dest = self.results[to_index]

                if isinstance(frm, Substance):  # Adding a substance is handled differently
                    if isinstance(dest, Container):
                        dest = Container.add(frm, dest, quantity)
                    elif isinstance(dest, PlateSlicer):
                        dest = Plate.add(frm, dest, quantity)
                elif isinstance(dest, Container):
                    frm, dest = Container.transfer(frm, dest, quantity)
                elif isinstance(dest, PlateSlicer):
                    frm, dest = Plate.transfer(frm, dest, quantity)

                self.results[frm_index] = frm
                self.results[to_index] = dest
            elif operation == 'solution':
                dest, solute, concentration, solvent, volume = rest
                to_index = self.indexes[dest]
                self.used.add(to_index)
                self.results[to_index] = Container.create_solution(solute, concentration, solvent, volume)
            elif operation == 'remove':
                what, dest = rest
                to_index = self.indexes[dest] if not isinstance(dest, PlateSlicer) else self.indexes[dest.plate]
                self.used.add(to_index)

                if isinstance(dest, PlateSlicer):
                    new_to = deepcopy(dest)
                    new_to.plate = self.results[to_index]
                    dest = new_to
                else:
                    dest = self.results[to_index]

                self.results[to_index] = dest.remove(what)
            elif operation == 'dilute':
                dest, solute, concentration, solvent, new_name = rest
                to_index = self.indexes[dest]
                self.results[to_index] = dest.dilute(solute, concentration, solvent, new_name)

        if len(self.used) != len(self.indexes):
            raise ValueError("Something declared as used wasn't used.")
        self.locked = True
        return [result for result in self.results if not isinstance(result, Substance)]


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

    @staticmethod
    def _add(frm, to, quantity):
        to = copy(to)
        to.plate = deepcopy(to.plate)
        result = numpy.vectorize(lambda elem: Container.add(frm, elem, quantity), cache=True)(to.get())
        if to.size == 1:
            to.set(result.item())
        else:
            to.set(result)
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
            result = numpy.vectorize(helper_func, cache=True)(to.get())
            if isinstance(to.get(), Container):  # A zero-dim array was returned.
                result = result.item()
            to.set(result)
            return frm_array[0], to.plate
        if not isinstance(frm, (Plate, PlateSlicer)):
            raise TypeError("Invalid source type.")

        to = copy(to)
        frm = copy(frm)

        if to.plate != frm.plate:
            to.plate = deepcopy(to.plate)
            frm.plate = deepcopy(frm.plate)
        else:
            to.plate = frm.plate = deepcopy(to.plate)

        if frm.size == 1:
            # Source from the single element in frm
            if frm.shape != ():
                raise RuntimeError("Shape of source should have been ()")

            def helper_func(elem):
                """ @private """
                frm_array[0], elem = Container.transfer(frm_array[0], elem, quantity)
                return elem

            frm_array = [frm.get()]
            result = numpy.vectorize(helper_func, cache=True)(to.get())
            to.set(result)
            frm.set(frm_array[0])

        elif to.size == 1:
            #  Replace the single element in self
            if to.shape != ():
                raise RuntimeError("Shape of source should have been ()")

            def helper_func(elem):
                """ @private """
                elem, to_array[0] = to_array[0].transfer(elem, quantity)
                return elem

            to_array = [to.get()]
            frm.set(numpy.vectorize(helper_func, cache=True)(frm.get()))
            to.set(to_array[0])

        elif frm.size == to.size and frm.shape == to.shape:
            def helper(elem1, elem2):
                """ @private """
                return Container.transfer(elem1, elem2, quantity)

            func = numpy.frompyfunc(helper, 2, 2)
            frm_result, to_result = func(frm.get(), to.get())
            frm.set(frm_result)
            to.set(to_result)
        else:
            raise ValueError("Source and destination slices must be the same size and shape.")

        return frm.plate, to.plate

    def volumes(self, substance: Substance = None, unit: str = 'uL') -> numpy.ndarray:
        """

        Arguments:
            unit:  unit to return volumes in.
            substance: (optional) Substance to display volumes of.

        Returns:
            numpy.ndarray of volumes for each well in uL

        """
        if substance is None:
            return numpy.vectorize(lambda elem: Unit.convert_from_storage(elem.volume, unit))(self.get())

        if not isinstance(substance, Substance):
            raise TypeError(f"Substance is not a valid type, {type(substance)}.")

        def helper(elem):
            """ Returns volume of elem. """
            if substance in elem.contents:
                quantity = f"{elem.contents[substance]} {config.moles_prefix}"
                return round(Unit.convert(substance, quantity, unit), config.external_precision)
            return 0

        return numpy.vectorize(helper)(self.get())

    def substances(self):
        """

        Returns: A set of substances present in the plate.

        """
        substances_arr = numpy.vectorize(lambda elem: elem.contents.keys())(self.get())
        return set.union(*map(set, substances_arr.flatten()))

    def moles(self, substance: Substance, unit: str = 'mol') -> numpy.ndarray:
        """
        Arguments:
            unit: unit to return moles in. ('mol', 'mmol', 'umol', etc.)
            substance: Substance to display moles of.

        Returns: moles of substance in each well.
        """

        if not isinstance(substance, Substance):
            raise TypeError(f"Substance is not a valid type, {type(substance)}.")

        def helper(elem):
            """ Returns moles of substance in elem. """
            if substance not in elem.contents:
                return 0
            quantity = f"{elem.contents[substance]} {config.moles_prefix}"
            return round(Unit.convert(substance, quantity, unit), config.external_precision)

        return numpy.vectorize(helper, cache=True)(self.get())

    def remove(self, what=Substance.LIQUID):
        """
        Removes substances from slice

        Arguments:
            what: What to remove. Can be a type of substance or a specific substance. Defaults to LIQUID.

        Returns: New Plate with requested substances removed.

        """
        result = numpy.vectorize(lambda elem: elem.remove(what), cache=True)(self.get())
        self.plate = deepcopy(self.plate)
        if result.size == 1:
            self.set(result.item())
        else:
            self.set(result)

        return self.plate
