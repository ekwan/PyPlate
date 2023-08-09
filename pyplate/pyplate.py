"""

pyplate: a tool for designing chemistry experiments in plate format

All classes in this package are friends and use private methods of other classes freely.

"""

# Allow typing reference while still building classes
from __future__ import annotations
import re
from typing import Tuple, Dict
import numpy
import yaml
from pyplate.slicer import Slicer

try:
    with open('../pyplate.yaml', 'r') as config_file:
        config = yaml.safe_load(config_file)
except (OSError, yaml.YAMLError):
    raise RuntimeError("Config file could not be read")


class Unit:
    """
    Provides unit conversion utility functions.
    """

    @staticmethod
    def convert_prefix_to_multiplier(prefix: str) -> float:
        """

        Converts an SI prefix into a multiplier.
        Example: "m" -> 1e-3, "u" -> 1e-6

        """
        if not isinstance(prefix, str):
            raise TypeError("SI prefix must be a string.")
        prefixes = {'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3, 'c': 1e-2, 'd': 1e-1, '': 1, 'k': 1e3, 'M': 1e6}
        if prefix in prefixes:
            return prefixes[prefix]
        raise ValueError(f"Invalid prefix: {prefix}")

    @staticmethod
    def extract_value_unit(s: str) -> Tuple[float, str]:
        """

        Splits an amount into a value and unit, converting any SI prefix.
        Example: '10 mL' -> (0.01, 'L')

        """
        if not isinstance(s, str):
            raise TypeError("Amount must be a string.")
        # (floating point number in 1.0e1 format) possibly some white space (alpha string)
        match = re.fullmatch(r"([_\d]+(?:\.\d+)?(?:e-?\d+)?)\s*([a-zA-Z]+)", s)
        if not match:
            raise ValueError("Invalid quantity.")
        value, unit = match.groups()
        value = float(value)
        if unit == 'U':
            return value, unit
        for base_unit in {'mol', 'g', 'L', 'M'}:
            if unit.endswith(base_unit):
                prefix = unit[:-len(base_unit)]
                value = value * Unit.convert_prefix_to_multiplier(prefix)
                return value, base_unit
        raise ValueError("Invalid unit.")

    @staticmethod
    def convert_to_unit_value(substance, how_much: str, volume: float = 0.0):
        """
        @private
        Converts amount to standard units.

        :param substance: Substance in question
        :param how_much: Amount of substance to convert
        :param volume: Volume of containing Mixture in mL
        :return: Value as per table below, but converted to storage format.

                 +--------+--------+--------+--------+--------+--------+
                 |              Valid Input                   | Output |
                 |    g   |    L   |   mol  |    M   |    U   |        |
        +--------+--------+--------+--------+--------+--------+--------+
        |SOLID   |   Yes  |   No   |   Yes  |   Yes  |   No   |   mol  |
        +--------+--------+--------+--------+--------+--------+--------+
        |LIQUID  |   Yes  |   Yes  |   Yes  |   ??   |   No   |   mL   |
        +--------+--------+--------+--------+--------+--------+--------+
        |ENZYME  |   No   |   No   |   No   |   No   |   Yes  |   U    |
        +--------+--------+--------+--------+--------+--------+--------+
        """

        value, unit = Unit.extract_value_unit(how_much)
        if substance.is_solid():  # Convert to moles
            if unit == 'g':  # mass
                result = value / substance.mol_weight
            elif unit == 'mol':  # moles
                result = value
            elif unit == 'M':  # molar
                if volume <= 0.0:
                    raise ValueError('Must have a liquid to add a molar concentration.')
                # value = molar concentration in mol/L, volume = volume in mL
                result = value * volume / 1000
            else:
                raise ValueError("We only measure solids in grams and moles.")
            return Unit.convert_to_storage(result, 'mol')
        elif substance.is_liquid():
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
        elif substance.is_enzyme():
            if unit == 'U':
                return value
            raise ValueError

    @staticmethod
    def convert_to_storage(value: float, unit: str):
        """

        Converts value to storage format.
        Example: (1, 'L') -> 1e6 uL

        """
        if unit[-1] == 'L':
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-1])
            result = value * prefix_value / config['volume_storage']
        else:  # moles
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-3])
            result = value * prefix_value / config['moles_storage']
        return round(result, config['internal_precision'])

    @staticmethod
    def convert_from_storage(value, unit):
        """

        Converts value from storage format.
        Example: (1e3 uL, 'mL') -> 1

        """
        if unit[-1] == 'L':
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-1])
            result = value * config['volume_storage'] / prefix_value
        else:  # moles
            prefix_value = Unit.convert_prefix_to_multiplier(unit[:-3])
            result = value * config['moles_storage'] / prefix_value
        return round(result, config['internal_precision'])


def is_integer(s):
    """
    Helper method to check if variable is integer.
    """
    try:
        int(s)
        return True
    except ValueError:
        return False


class Substance:
    """
    An abstract chemical or biological entity (e.g., reagent, enzyme, solvent, etc.). Immutable.
    Solids and enzymes are assumed to require zero volume.
    """
    SOLID = 1
    LIQUID = 2
    ENZYME = 3

    def __init__(self, name: str, mol_type: int, molecule=None):
        """
        Create a new substance.

        Args:
            name: Name of substance.
            mol_type: Substance.LIQUID, Substance.SOLID, or Substance.ENZYME.
            molecule: (optional) A cctk molecule.
        """
        self.name = name
        self._type = mol_type
        self.mol_weight = self.density = self.concentration = None
        self.molecule = molecule

    def __repr__(self):
        if self.is_solid():
            return f"SOLID ({self.name}: {self.mol_weight})"
        if self.is_liquid():
            return f"LIQUID ({self.name}: {self.mol_weight}, {self.density})"
        else:
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

        Args:
            name: Name of substance.
            mol_weight: Molecular weight in g/mol
            molecule: (optional) cctk molecule

        Returns: New substance.

        """
        substance = Substance(name, Substance.SOLID, molecule)
        substance.mol_weight = mol_weight
        return substance

    @staticmethod
    def liquid(name: str, mol_weight: float, density: float, molecule=None) -> Substance:
        """
        Creates a liquid substance.

        Args:
            name: Name of substance.
            mol_weight: Molecular weight in g/mol
            density: Density in g/mL
            molecule: (optional) cctk molecule

        Returns: New substance.

        """
        substance = Substance(name, Substance.LIQUID, molecule)
        substance.mol_weight = mol_weight  # g / mol
        substance.density = density  # g / mL
        substance.concentration = density / mol_weight  # mol / mL
        return substance

    @staticmethod
    def enzyme(name: str, molecule=None):
        """
        Creates an enzyme.

        Args:
            name: Name of enzyme.
            molecule: (optional) cctk molecule

        Returns: New substance.

        """
        return Substance(name, Substance.ENZYME, molecule)

    def is_solid(self):
        """
        Return true if Substance is a solid.
        """
        return self._type == Substance.SOLID

    def is_liquid(self):
        """
        Return true if Substance is a liquid.
        """
        return self._type == Substance.LIQUID

    def is_enzyme(self):
        """
        Return true if Substance is an enzyme.
        """
        return self._type == Substance.ENZYME


class Container:
    """
    Stores specified quantities of Substances in a vessel with a given maximum volume. Immutable.
    """

    def __init__(self, name, max_volume=float('inf'), initial_contents=None):
        """
        Create a Container.

        Args:
            name: Name of container
            max_volume: Maximum volume that can be stored in the container in mL
            initial_contents: (optional) Iterable of tuples of the form (Substance, quantity)
        """
        self.name = name
        self.contents: Dict[Substance, float] = dict()
        self.volume = 0.0
        self.max_volume = Unit.convert_to_storage(max_volume, 'mL')
        if initial_contents:
            for substance, how_much in initial_contents:
                self._self_add(substance, how_much)

    def copy(self) -> Container:
        """
        Clones current Container.
        """
        new_container = Container(self.name, self.max_volume)
        new_container.contents = self.contents.copy()
        new_container.volume = self.volume
        new_container.max_volume = self.max_volume  # Don't readjust this value
        return new_container

    def __eq__(self, other):
        if not isinstance(other, Container):
            return False
        return self.name == other.name and self.contents == other.contents and \
            self.volume == other.volume and self.max_volume == other.max_volume

    def __hash__(self):
        return hash((self.name, self.volume, self.max_volume, *tuple(map(tuple, self.contents.items()))))

    def _self_add(self, source: Substance, how_much: str) -> None:
        """

        Adds to current Container, mutating it.
        Only to be used in the constructor and immediately after copy

        Args:
            source: Substance to add.
            how_much: How much to add. ('10 mol')

        """
        if not isinstance(source, Substance):
            raise TypeError("Invalid source type.")
        if how_much.endswith('M') and not source.is_solid():
            # TODO: molarity from liquids?
            raise ValueError("Molarity solutions can only be made from solids.")
        volume = Unit.convert_from_storage(self.volume, 'mL')
        amount_to_transfer = round(Unit.convert_to_unit_value(source, how_much, volume), config['internal_precision'])
        self.contents[source] = round(self.contents.get(source, 0) + amount_to_transfer, config['internal_precision'])
        if source.is_liquid():
            self.volume = round(self.volume + amount_to_transfer, config['internal_precision'])
        if self.volume > self.max_volume:
            raise ValueError("Exceeded maximum volume")

    def _transfer(self, source_container: Container, volume: str):
        """ transfer volume ('10 mL') from container to self """
        if not isinstance(source_container, Container):
            raise TypeError("Invalid source type.")
        volume_to_transfer, unit = Unit.extract_value_unit(volume)
        volume_to_transfer = Unit.convert_to_storage(volume_to_transfer, 'L')
        volume_to_transfer = round(volume_to_transfer, config['internal_precision'])
        if unit != 'L':
            raise ValueError("We can only transfer liquid from other containers.")
        if volume_to_transfer > source_container.volume:
            raise ValueError("Not enough mixture left in source container." +
                             f" {Unit.convert_from_storage(volume_to_transfer, 'mL')} mL "
                             f" needed of {source_container.name}" +
                             f" out of {Unit.convert_from_storage(source_container.volume, 'mL')} mL.")
        source_container, to = source_container.copy(), self.copy()
        ratio = volume_to_transfer / source_container.volume
        for substance, amount in source_container.contents.items():
            to.contents[substance] = round(to.contents.get(substance, 0) + amount * ratio, config['internal_precision'])
            source_container.contents[substance] = round(source_container.contents[substance] - amount * ratio,
                                                         config['internal_precision'])
        to.volume = round(to.volume + volume_to_transfer, config['internal_precision'])
        if to.volume > to.max_volume:
            raise ValueError(f"Exceeded maximum volume in {to.name}.")
        source_container.volume = round(source_container.volume - volume_to_transfer, config['internal_precision'])
        return source_container, to

    def _transfer_slice(self, source_slice, volume):
        """
        Transfer volume ('10 mL') from slice to self

        Returns:
            A tuple of a new plate and a new container, both modified.
        """

        def helper_func(elem):
            """ Moves volume from elem to to_array[0]"""
            elem, to_array[0] = Container.transfer(elem, to_array[0], volume)
            return elem

        if isinstance(source_slice, Plate):
            source_slice = source_slice[:]
        if not isinstance(source_slice, PlateSlicer):
            raise TypeError("Invalid source type.")
        to = self.copy()
        source_slice = source_slice.copy()
        source_slice.plate = source_slice.plate.copy()
        volume_to_transfer, unit = Unit.extract_value_unit(volume)
        volume_to_transfer = Unit.convert_to_storage(volume_to_transfer, 'L')
        # volume_to_transfer *= 1000.0  # convert L to mL
        volume_to_transfer = round(volume_to_transfer, config['internal_precision'])
        if unit != 'L':
            raise ValueError("We can only transfer liquid from other containers.")
        if source_slice.get().size * volume_to_transfer > (to.max_volume - to.volume):
            raise ValueError("Not enough room left in destination container.")

        to_array = [to]
        result = numpy.vectorize(helper_func, cache=True)(source_slice.get())
        source_slice.set(result)
        return source_slice.plate, to_array[0]

    def __repr__(self):
        max_volume = ('/' + str(Unit.convert_from_storage(self.max_volume, 'mL'))) \
            if self.max_volume != float('inf') else ''
        return f"Container ({self.name}) ({Unit.convert_from_storage(self.volume, 'mL')}" + \
            f"{max_volume} of ({self.contents})"

    @staticmethod
    def add(source: Substance, destination: Container, how_much: str) -> Container:
        """
        Move the given quantity ('10 mol') of the source substance to the destination container.

        Returns:
            A new copy of destination.
        """
        if not isinstance(destination, Container):
            raise TypeError("You can only use Container.add to add to a Container")
        destination = destination.copy()
        destination._self_add(source, how_much)
        return destination

    @staticmethod
    def transfer(source, destination: Container, volume):
        """
        Move volume ('10 mL') from source to destination container,
        returning copies of the objects with amounts adjusted accordingly.

        Returns:
            A tuple of (T, Container) where T is the type of the source.
        """
        if not isinstance(destination, Container):
            raise TypeError("You can only use Container.transfer into a Container")
        if isinstance(source, Container):
            return destination._transfer(source, volume)
        elif isinstance(source, (Plate, PlateSlicer)):
            return destination._transfer_slice(source, volume)
        else:
            raise TypeError("Invalid source type.")

    @staticmethod
    def create_stock_solution(what: Substance, concentration: float, solvent: Substance, volume: float):
        """
        Create a stock solution.

        Args:
            what: What to dilute.
            concentration: Desired concentration in mol/L
            solvent: What to dilute with.
            volume: Desired total volume in mL.

        Returns:
            New container with desired solution.
        """
        container = Container(f"{what.name} {concentration:.2}M", max_volume=volume)
        moles_to_add = volume * concentration
        if what.is_enzyme():
            raise TypeError("You can't add enzymes by molarity.")
        elif what.is_solid():
            container = container.add(solvent, container, f"{volume} mL")
            container = container.add(what, container, f"{round(moles_to_add, config['internal_precision'])} mol")
        else:  # Liquid
            volume_to_add = round(moles_to_add * what.mol_weight / (what.density * 1000), config['external_precision'])
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
            # self.row_names = [f"{i + 1}" for i in range(rows)]
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
                if is_integer(row):
                    raise ValueError(
                        f"please don't confuse me with row names that are integers ({row})"
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
        except (ValueError, OverflowError):
            raise ValueError(f"invalid max volume per well {max_volume_per_well}")

        if isinstance(columns, int):
            if columns < 1:
                raise ValueError("illegal number of columns")
            self.n_columns = columns
            self.column_names = [f"{i + 1}" for i in range(columns)]
        elif isinstance(columns, list):
            if len(columns) == 0:
                raise ValueError("must have at least one row")
            for column in columns:
                if not isinstance(column, str):
                    raise ValueError("row names must be strings")
                if len(column.strip()) == 0:
                    raise ValueError(
                        "zero length strings are not allowed as column labels"
                    )
                if is_integer(column):
                    raise ValueError(
                        f"please don't confuse me with column names that are integers({column})"
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

    def volumes(self, substance=None):
        """

        Args:
            substance: (optional) Substance to display volumes of.

        Returns:
            numpy.ndarray of volumes for each well in uL

        """
        if substance is None:
            return numpy.vectorize(lambda elem: Unit.convert_from_storage(elem.volume, 'uL'))(self.wells)
        else:
            def helper(elem):
                """ Returns volume of elem. """
                if substance.is_liquid() and substance in elem.contents:
                    return round(Unit.convert_from_storage(elem.contents[substance], 'uL'), config['external_precision'])
                else:
                    return 0

            return numpy.vectorize(helper)(self.wells)

    def substances(self):
        """

        Returns: A set of substances present in the plate.

        """
        substances_arr = numpy.vectorize(lambda elem: elem.contents.keys())(self.wells)
        return set.union(*map(set, substances_arr.flatten()))

    def moles(self, substance):
        """
        Returns: moles of substance in each well.
        """

        def helper(elem):
            """ Returns moles of substance in elem. """
            if substance not in elem.contents:
                return 0
            if substance.is_liquid():
                return round(Unit.convert_from_storage(elem.contents[substance], 'mL') * substance.density /
                             substance.mol_weight, config['external_precision'])
            elif substance.is_solid():
                return round(Unit.convert_from_storage(elem.contents[substance], 'mol'), config['external_precision'])

        return numpy.vectorize(helper, cache=True)(self.wells)

    def volume(self):
        """
        Returns: total volume stored in plate in uL.
        """
        return self.volumes().sum()

    def copy(self):
        """
        Returns: A clone of the current plate.
        """
        new_plate = Plate(self.name, self.max_volume_per_well, self.make, 1, 1)
        new_plate.n_rows, new_plate.n_columns = self.n_rows, self.n_columns
        new_plate.row_names, new_plate.column_names = self.row_names, self.column_names
        new_plate.max_volume_per_well = self.max_volume_per_well  # Don't readjust this value
        new_plate.wells = self.wells.copy()
        return new_plate

    @staticmethod
    def add(source: Substance, destination: Plate | PlateSlicer, how_much):
        """
        Move the given quantity ('10 mol') of the source substance to the destination.

        Returns:
            A new copy of destination plate.
        """
        if not isinstance(destination, (Plate, PlateSlicer)):
            raise TypeError("You can only use Plate.add to add to a Plate")
        if isinstance(destination, Plate):
            destination = destination[:]
        # noinspection PyProtectedMember
        return PlateSlicer._add(source, destination, how_much)

    @staticmethod
    def transfer(source, destination: Plate | PlateSlicer, volume):
        """
        Move volume ('10 mL') from source to destination,
        returning copies of the objects with amounts adjusted accordingly.

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
    """

    def __init__(self):
        self.indexes = dict()
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
                    self.results.append(arg.copy())
        return self

    def add(self, source, destination, how_much):
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
            raise ValueError("Destination not found in declared uses.")
        if isinstance(destination, Plate):
            destination = destination[:]
        self.steps.append(('add', source, destination, how_much))
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
            raise ValueError("Destination not found in declared uses.")
        if isinstance(source, Plate):
            source = source[:]
        if isinstance(destination, Plate):
            destination = destination[:]
        self.steps.append(('transfer', source, destination, volume))
        return self

    def create_container(self, name, max_volume, initial_contents=None):

        """
        Adds a step to the recipe which creates a container.

        Args:
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
            for substance, how_much in initial_contents:
                if not isinstance(substance, Substance):
                    raise ValueError("Containers can only be created from substances.")
                self.steps.append(('add', substance, new_container, how_much))
        return new_container

    def create_stock_solution(self, what: Substance, concentration: float, solvent: Substance, volume: float):
        """

        Adds a step to the recipe which creates a stock solution.

        Args:
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
                frm, to, how_much = rest
                to_index = self.indexes[to] if not isinstance(to, PlateSlicer) else self.indexes[to.plate]

                # containers and such can change while building the recipe
                if isinstance(to, PlateSlicer):
                    new_to = to.copy()
                    new_to.plate = self.results[to_index]
                    to = new_to
                else:
                    to = self.results[to_index]

                if isinstance(to, Container):
                    to = Container.add(frm, to, how_much)
                elif isinstance(to, PlateSlicer):
                    to = Plate.add(frm, to, how_much)

                self.results[to_index] = to
                self.used.add(to_index)
            elif operation == 'transfer':
                frm, to, how_much = rest
                # used items can change in a recipe
                frm_index = self.indexes[frm] if not isinstance(frm, PlateSlicer) else self.indexes[frm.plate]
                to_index = self.indexes[to] if not isinstance(to, PlateSlicer) else self.indexes[to.plate]

                self.used.add(frm_index)
                self.used.add(to_index)

                # containers and such can change while baking the recipe
                if isinstance(frm, PlateSlicer):
                    new_frm = frm.copy()
                    new_frm.plate = self.results[frm_index]
                    frm = new_frm
                else:
                    frm = self.results[frm_index]

                if isinstance(to, PlateSlicer):
                    new_to = to.copy()
                    new_to.plate = self.results[to_index]
                    to = new_to
                else:
                    to = self.results[to_index]

                if isinstance(frm, Substance):  # Adding a substance is handled differently
                    if isinstance(to, Container):
                        to = Container.add(frm, to, how_much)
                    elif isinstance(to, PlateSlicer):
                        to = Plate.add(frm, to, how_much)
                    # to = to.add(frm, how_much)
                elif isinstance(to, Container):
                    frm, to = Container.transfer(frm, to, how_much)
                elif isinstance(to, PlateSlicer):
                    frm, to = Plate.transfer(frm, to, how_much)

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

    def copy(self):
        """ @private """
        return PlateSlicer(self.plate, self.item)

    @staticmethod
    def _add(frm, to, how_much):
        to = to.copy()
        to.plate = to.plate.copy()
        result = numpy.vectorize(lambda elem: Container.add(frm, elem, how_much), cache=True)(to.get())
        to.set(result)
        return to.plate

    @staticmethod
    def _transfer(frm, to, how_much):
        if isinstance(frm, Container):
            to = to.copy()
            to.plate = to.plate.copy()

            def helper_func(elem):
                """ @private """
                frm_array[0], elem = Container.transfer(frm_array[0], elem, how_much)
                return elem

            frm_array = [frm]
            result = numpy.vectorize(helper_func, cache=True)(to.get())
            if isinstance(to.get(), Container):  # A zero-dim array was returned.
                result = result.item()
            to.set(result)
            return frm_array[0], to.plate
        elif not isinstance(frm, (Plate, PlateSlicer)):
            raise TypeError("Invalid source type.")

        to = to.copy()
        frm = frm.copy()

        if to.plate != frm.plate:
            to.plate = to.plate.copy()
            frm.plate = frm.plate.copy()
        else:
            to.plate = frm.plate = to.plate.copy()

        if frm.size == 1:
            # Source from the single element in frm
            if frm.shape != ():
                raise RuntimeError("Shape of source should have been ()")

            def helper_func(elem):
                """ @private """
                frm_array[0], elem = Container.transfer(frm_array[0], elem, how_much)
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
                elem, to_array[0] = to_array[0].transfer(elem, how_much)
                return elem

            to_array = [to.get()]
            frm.set(numpy.vectorize(helper_func, cache=True)(frm.get()))
            to.set(to_array[0])

        elif frm.size == to.size and frm.shape == to.shape:
            def helper(elem1, elem2):
                """ @private """
                return Container.transfer(elem1, elem2, how_much)

            func = numpy.frompyfunc(helper, 2, 2)
            frm_result, to_result = func(frm.get(), to.get())
            frm.set(frm_result)
            to.set(to_result)
        else:
            raise ValueError("Source and destination slices must be the same size and shape.")

        return frm.plate, to.plate
