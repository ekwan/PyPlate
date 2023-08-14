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
import re
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
            raise TypeError("Amount must be a string.")
        # (floating point number in 1.0e1 format) possibly some white space (alpha string)
        match = re.fullmatch(r"([_\d]+(?:\.\d+)?(?:e-?\d+)?)\s*([a-zA-Z]+)", quantity)
        if not match:
            raise ValueError("Invalid quantity. Quantity should be in the format '10 mL'.")
        value, unit = match.groups()
        value = float(value)
        if unit == 'U':
            return value, unit
        for base_unit in ['mol', 'g', 'L', 'M']:
            if unit.endswith(base_unit):
                prefix = unit[:-len(base_unit)]
                value = value * Unit.convert_prefix_to_multiplier(prefix)
                return value, base_unit
        raise ValueError("Invalid unit {base_unit}.")

    @staticmethod
    def convert_to_unit_value(substance: Substance, quantity: str, volume: float = 0.0) -> float:
        """

        Converts amount to standard unit.


        Arguments:
            substance: Substance in question.
            quantity: Quantity of substance.
            volume: Volume of containing Mixture in mL

        Returns: Value in standard unit, converted to storage format.

        ---

        Standard units:

        - SOLID: moles

        - LIQUID: liter

        - ENZYME: activity unit

        """

        #          +--------+--------+--------+--------+--------+----------+
        #          |              Valid Input                   | Standard |
        #          |    g   |    L   |   mol  |    M   |    U   |   Unit   |
        # +--------+--------+--------+--------+--------+--------+----------+
        # |SOLID   |   Yes  |   No   |   Yes  |   Yes  |   No   |    mol   |
        # +--------+--------+--------+--------+--------+--------+----------+
        # |LIQUID  |   Yes  |   Yes  |   Yes  |   No   |   No   |    mL    |
        # +--------+--------+--------+--------+--------+--------+----------+
        # |ENZYME  |   No   |   No   |   No   |   No   |   Yes  |    U     |
        # +--------+--------+--------+--------+--------+--------+----------+

        # TODO: Explain why moles and mL were chosen as units.
        # TODO: Enzyme could be in solution.

        if not isinstance(substance, Substance):
            raise TypeError(f"Invalid type for substance, {type(substance)}")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")
        if not isinstance(volume, float):
            raise TypeError("Volume, if provided, must be a float.")

        value, unit = Unit.parse_quantity(quantity)
        if substance.is_solid():  # Convert to moles
            if unit == 'g':  # mass
                result = value / substance.mol_weight
            elif unit == 'mol':  # moles
                result = value
            elif unit == 'M':  # molar
                # A molar concentration with zero volume would be undefined.
                if volume <= 0.0:
                    raise ValueError('Must have a liquid in which to dissolve the solid ' +
                                     'in order to create a molar concentration')
                # value = molar concentration in mol/L, volume = volume in mL
                result = value * volume / 1000
            else:
                raise ValueError("We only measure solids in grams and moles.")
            return Unit.convert_to_storage(result, 'mol')
        if substance.is_liquid():
            if unit == 'g':  # mass
                # g -> mL
                result = value / substance.density
            elif unit == 'L':  # volume
                result = value * 1000
            elif unit == 'mol':  # moles
                # mol -> mL
                result = value / substance.concentration
            else:
                raise ValueError
            return Unit.convert_to_storage(result, 'mL')
        if substance.is_enzyme():
            if unit == 'U':
                return value
            raise ValueError

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
            result = value * prefix_value / config.volume_storage
        else:  # moles
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-3])
            result = value * prefix_value / config.moles_storage
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
        if not isinstance(value, float):
            raise TypeError("Value must be a float.")
        if not isinstance(unit, str):
            raise TypeError("Unit must be a str.")

        if unit[-1] == 'L':
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-1])
            result = value * config.volume_storage / prefix_value
        else:  # moles
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-3])
            result = value * config.moles_storage / prefix_value
        return round(result, config.internal_precision)


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

        self.name = name
        self._type = mol_type
        self.mol_weight = self.density = self.concentration = None
        self.molecule = molecule

    def __repr__(self):
        if self.is_solid():
            return f"SOLID ({self.name}: {self.mol_weight})"
        if self.is_liquid():
            return f"LIQUID ({self.name}: {self.mol_weight}, {self.density})"
        return f"ENZYME ({self.name})"

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
        if not isinstance(mol_weight, float):
            raise TypeError("Molecular weight must be a float.")

        substance = Substance(name, Substance.SOLID, molecule)
        substance.mol_weight = mol_weight
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
        if not isinstance(mol_weight, float):
            raise TypeError("Molecular weight must be a float.")

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

    def __init__(self, name: str, max_volume: float = float('inf'),
                 initial_contents: Iterable[Tuple[Substance, str]] = None):
        """
        Create a Container.

        Arguments:
            name: Name of container
            max_volume: Maximum volume that can be stored in the container in mL
            initial_contents: (optional) Iterable of tuples of the form (Substance, quantity)
        """
        # TODO: make max_volume a str
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        if not isinstance(max_volume, (int, float)):
            raise TypeError("Maximum volume must be a float.")
        self.name = name
        self.contents: Dict[Substance, float] = {}
        self.volume = 0.0
        self.max_volume = Unit.convert_to_storage(max_volume, 'mL')
        if initial_contents:
            if not isinstance(initial_contents, Iterable):
                raise TypeError("Initial contents must be iterable.")
            for substance, quantity in initial_contents:
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
        if quantity.endswith('M') and not source.is_solid():
            # TODO: molarity from liquids?
            raise ValueError("Molarity solutions can only be made from solids.")
        volume = Unit.convert_from_storage(self.volume, 'mL')
        amount_to_transfer = round(Unit.convert_to_unit_value(source, quantity, volume), config.internal_precision)
        # add source Substance to self.contents
        self.contents[source] = round(self.contents.get(source, 0) + amount_to_transfer, config.internal_precision)
        if source.is_liquid():
            self.volume = round(self.volume + amount_to_transfer, config.internal_precision)
        if self.volume > self.max_volume:
            raise ValueError("Exceeded maximum volume")

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
            raise ValueError("Not enough mixture left in source container." +
                             f" {Unit.convert_from_storage(volume_to_transfer, 'mL')} mL "
                             f" needed of {source_container.name}" +
                             f" out of {Unit.convert_from_storage(source_container.volume, 'mL')} mL.")
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
        if source_slice.get().size * volume_to_transfer > (to.max_volume - to.volume):
            raise ValueError(f"Exceeded maximum volume in {to.name}.")

        to_array = [to]
        result = numpy.vectorize(helper_func, cache=True)(source_slice.get())
        source_slice.set(result)
        return source_slice.plate, to_array[0]

    def __repr__(self):
        max_volume = ('/' + str(Unit.convert_from_storage(self.max_volume, 'mL'))) \
            if self.max_volume != float('inf') else ''
        return f"Container ({self.name}) ({Unit.convert_from_storage(self.volume, 'mL')}" + \
            f"{max_volume} mL of ({self.contents})"

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
    def transfer(source: Container or Plate or PlateSlicer, destination: Container, volume):
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
    def create_stock_solution(what: Substance, concentration: float, solvent: Substance, volume: float):
        """
        Create a stock solution.

        Note: solids are assumed to have zero volume.

        Arguments:
            what: What to dissolve.
            concentration: Desired concentration in mol/L.
            solvent: What to dissolve with.
            volume: Desired total volume in mL.

        Returns:
            New container with desired solution.
        """
        container = Container(f"{what.name} {concentration:.2}M", max_volume=volume)
        moles_to_add = volume * concentration
        if what.is_enzyme():
            raise TypeError("You can't add enzymes by molarity.")
        if what.is_solid():
            container = container.add(solvent, container, f"{volume} mL")
            container = container.add(what, container, f"{round(moles_to_add, config.internal_precision)} mol")
        else:  # Liquid
            volume_to_add = round(moles_to_add * what.mol_weight / (what.density * 1000), config.external_precision)
            container = container.add(solvent, container, f"{volume - volume_to_add} mL")
            container = container.add(what, container, f"{volume_to_add} mL")
        return container


class Plate:
    """
    A spatially ordered collection of Containers, like a 96 well plate.
    The spatial arrangement must be rectangular. Immutable.
    """

    def __init__(self, name: str, max_volume_per_well: float, make: str = "generic", rows=8, columns=12):
        """
            Creates a generic plate.

            Attributes:
                name: name of plate
                max_volume_per_well: maximum volume of each well in uL
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

        if isinstance(rows, int):
            if rows < 1:
                raise ValueError("illegal number of rows")
            self.n_rows = rows
            self.row_names = []
            for n in range(1, rows + 1):
                result = []
                while n > 0:
                    n -= 1
                    result.append(chr(ord('A') + n % 26))
                    n //= 26
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

        try:
            max_volume_per_well = float(max_volume_per_well)
            if max_volume_per_well <= 0:
                raise ValueError("max volume per well must be greater than zero")
            self.max_volume_per_well = Unit.convert_to_storage(max_volume_per_well, 'uL')
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"invalid max volume per well {max_volume_per_well}") from exc

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
                                             max_volume=Unit.convert_from_storage(self.max_volume_per_well, 'mL'))
                                   for col in range(self.n_columns)] for row in range(self.n_rows)])

    def __getitem__(self, item) -> PlateSlicer:
        return PlateSlicer(self, item)

    def __repr__(self):
        return f"Plate: {self.name}"

    def volumes(self, substance: Substance = None) -> numpy.ndarray:
        """

        Arguments:
            substance: (optional) Substance to display volumes of.

        Returns:
            numpy.ndarray of volumes for each well in uL

        """
        if substance is None:
            return numpy.vectorize(lambda elem: Unit.convert_from_storage(elem.volume, 'uL'))(self.wells)

        if not isinstance(substance, Substance):
            raise TypeError(f"Substance is not a valid type, {type(substance)}.")

        def helper(elem):
            """ Returns volume of elem. """
            if substance.is_liquid() and substance in elem.contents:
                return round(Unit.convert_from_storage(elem.contents[substance], 'uL'),
                             config.external_precision)
            return 0

        return numpy.vectorize(helper)(self.wells)

    def substances(self):
        """

        Returns: A set of substances present in the plate.

        """
        substances_arr = numpy.vectorize(lambda elem: elem.contents.keys())(self.wells)
        return set.union(*map(set, substances_arr.flatten()))

    def moles(self, substance: Substance) -> numpy.ndarray:
        """
        Arguments:
            substance: Substance to display moles of.

        Returns: moles of substance in each well.
        """

        if not isinstance(substance, Substance):
            raise TypeError(f"Substance is not a valid type, {type(substance)}.")

        def helper(elem):
            """ Returns moles of substance in elem. """
            if substance not in elem.contents:
                return 0
            if substance.is_liquid():
                return round(Unit.convert_from_storage(elem.contents[substance], 'mL') * substance.density /
                             substance.mol_weight, config.external_precision)
            if substance.is_solid():
                return round(Unit.convert_from_storage(elem.contents[substance], 'mol'), config.external_precision)

        return numpy.vectorize(helper, cache=True)(self.wells)

    def volume(self):
        """
        Returns: total volume stored in plate in uL.
        """
        return self.volumes().sum()

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
    def transfer(source, destination: Plate | PlateSlicer, volume):
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
                self.indexes[arg] = len(self.results)
                if isinstance(arg, Substance):
                    self.results.append(arg)
                else:
                    self.results.append(deepcopy(arg))
        return self

    def add(self, source, destination, quantity):
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
        if isinstance(source, Plate):
            source = source[:]
        if isinstance(destination, Plate):
            destination = destination[:]
        self.steps.append(('transfer', source, destination, volume))
        return self

    def create_container(self, name, max_volume, initial_contents=None):

        """
        Adds a step to the recipe which creates a container.

        Arguments:
            name: Name of container
            max_volume: Maximum volume that can be stored in the container in mL
            initial_contents: (optional) Iterable of tuples of the form (Substance, quantity)

        Returns:
            A new Container so that it may be used in later recipe steps.
        """
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        new_container = Container(name, max_volume)
        self.uses(new_container)
        if initial_contents:
            for substance, quantity in initial_contents:
                if not isinstance(substance, Substance):
                    raise ValueError("Containers can only be created from substances.")
                self.steps.append(('add', substance, new_container, quantity))
        return new_container

    def create_stock_solution(self, what: Substance, concentration: float, solvent: Substance, volume: float):
        """

        Adds a step to the recipe which creates a stock solution.

        Arguments:
            what: What to dilute.
            concentration: Desired concentration in mol/L
            solvent: What to dilute with.
            volume: Desired total volume in mL.

        Returns:
            A new Container so that it may be used in later recipe steps.

        """
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        new_container = Container("{what.name} {concentration:.2}M", max_volume=volume)
        self.uses(new_container)
        self.steps.append(('stock', new_container, what, concentration, solvent, volume))
        return new_container

    def bake(self):
        """
        Completes steps stored in recipe.
        Checks validity of each step and ensures all declared objects have been used.
        Locks Recipe from further modification.

        Returns:
            Copies of all used objects in the order they were declared.

        """
        for operation, *rest in self.steps:
            if operation == 'add':
                frm, to, quantity = rest
                to_index = self.indexes[to] if not isinstance(to, PlateSlicer) else self.indexes[to.plate]

                # containers and such can change while building the recipe
                if isinstance(to, PlateSlicer):
                    new_to = deepcopy(to)
                    new_to.plate = self.results[to_index]
                    to = new_to
                else:
                    to = self.results[to_index]

                if isinstance(to, Container):
                    to = Container.add(frm, to, quantity)
                elif isinstance(to, PlateSlicer):
                    to = Plate.add(frm, to, quantity)

                self.results[to_index] = to
                self.used.add(to_index)
            elif operation == 'transfer':
                frm, to, quantity = rest
                # used items can change in a recipe
                frm_index = self.indexes[frm] if not isinstance(frm, PlateSlicer) else self.indexes[frm.plate]
                to_index = self.indexes[to] if not isinstance(to, PlateSlicer) else self.indexes[to.plate]

                self.used.add(frm_index)
                self.used.add(to_index)

                # containers and such can change while baking the recipe
                if isinstance(frm, PlateSlicer):
                    new_frm = deepcopy(frm)
                    new_frm.plate = self.results[frm_index]
                    frm = new_frm
                else:
                    frm = self.results[frm_index]

                if isinstance(to, PlateSlicer):
                    new_to = deepcopy(to)
                    new_to.plate = self.results[to_index]
                    to = new_to
                else:
                    to = self.results[to_index]

                if isinstance(frm, Substance):  # Adding a substance is handled differently
                    if isinstance(to, Container):
                        to = Container.add(frm, to, quantity)
                    elif isinstance(to, PlateSlicer):
                        to = Plate.add(frm, to, quantity)
                elif isinstance(to, Container):
                    frm, to = Container.transfer(frm, to, quantity)
                elif isinstance(to, PlateSlicer):
                    frm, to = Plate.transfer(frm, to, quantity)

                self.results[frm_index] = frm
                self.results[to_index] = to
            elif operation == 'stock':
                to, what, concentration, solvent, volume = rest
                to_index = self.indexes[to]
                self.used.add(to_index)
                self.results[to_index] = Container.create_stock_solution(what, concentration, solvent, volume)

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
