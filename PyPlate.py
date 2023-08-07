# Allow typing reference while still building classes
from __future__ import annotations
import re
from typing import Tuple, Dict
import numpy
from Slicer import Slicer

EXTERNAL_PRECISION = 3
INTERNAL_PRECISION = 10
# VOLUME_STORAGE = 1e-3   # mL
# MOLES_STORAGE = 1e-3    # mmol
VOLUME_STORAGE = 1e-6  # uL
MOLES_STORAGE = 1e-6  # umol


class Unit:
    @staticmethod
    def convert_prefix(prefix):
        prefixes = {'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3, 'c': 1e-2, 'd': 1e-1, '': 1, 'k': 1e3, 'M': 1e6}
        if prefix in prefixes:
            return prefixes[prefix]
        raise ValueError(f"Invalid prefix: {prefix}")

    @staticmethod
    def extract_value_unit(s: str) -> Tuple[float, str]:
        if not isinstance(s, str):
            raise TypeError
        # (floating point number in 1.0e1 format) possibly some white space (alpha string)
        match = re.fullmatch(r"([_\d]+(?:\.\d+)?(?:e-?\d+)?)\s*([a-zA-Z]+)", s)
        if not match:
            raise ValueError("Invalid quantity.")
        value, unit = match.groups()
        value = float(value)
        if unit == 'AU':
            return value, unit
        for base_unit in {'mol', 'g', 'L', 'M'}:
            if unit.endswith(base_unit):
                prefix = unit[:-len(base_unit)]
                value = value * Unit.convert_prefix(prefix)
                return value, base_unit
        raise ValueError("Invalid unit.")

    @staticmethod
    def convert_to_unit_value(substance, how_much: str, volume: float = 0.0):  # mol, mL or AU
        """
        @private
        Converts amount to standard units.

        :param substance: Substance in question
        :param how_much: Amount of substance to convert
        :param volume: Volume of containing Mixture in mL
        :return: float

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
                return value / substance.mol_weight
            elif unit == 'mol':  # moles
                return value
            elif unit == 'M':  # molar
                if volume <= 0.0:
                    raise ValueError('Must have a liquid to add a molar concentration.')
                # value = molar concentration in mol/L, volume = volume in mL
                return value * volume / 1000
            raise ValueError("We only measure solids in grams and moles.")
        elif substance.is_liquid():  # Convert to VOLUME_STORAGE L
            if unit == 'g':  # mass
                # g -> mL -> L -> VOLUME_STORAGE
                return value / substance.density
            elif unit == 'L':  # volume
                return value * 1000
            elif unit == 'mol':  # moles
                # mol -> mL -> L -> VOLUME_STORAGE
                return value / substance.concentration / 1000
            raise ValueError
        elif substance.is_enzyme():
            if unit == 'U':
                return value
            raise ValueError


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
    SOLID = 1
    LIQUID = 2
    ENZYME = 3

    def __init__(self, name, mol_type, molecule=None):
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
    def solid(name, mol_weight, molecule=None):
        substance = Substance(name, Substance.SOLID, molecule)
        substance.mol_weight = mol_weight
        return substance

    @staticmethod
    def liquid(name, mol_weight, density, molecule=None):
        substance = Substance(name, Substance.LIQUID, molecule)
        substance.mol_weight = mol_weight  # g / mol
        substance.density = density  # g / mL
        substance.concentration = 1000.0 * density / mol_weight  # mol / L
        return substance

    @staticmethod
    def enzyme(name, molecule=None):
        return Substance(name, Substance.ENZYME, molecule)

    def is_solid(self):
        return self._type == Substance.SOLID

    def is_liquid(self):
        return self._type == Substance.LIQUID

    def is_enzyme(self):
        return self._type == Substance.ENZYME


class Container:
    def __init__(self, name, max_volume=float('inf'), initial_contents=None):
        self.name = name
        self.contents: Dict[Substance, float] = dict()
        self.volume = 0.0
        self.max_volume = max_volume
        if initial_contents:
            for substance, how_much in initial_contents:
                self._self_add(substance, how_much)

    def copy(self):
        new_container = Container(self.name, self.max_volume)
        new_container.contents = self.contents.copy()
        new_container.volume = self.volume
        return new_container

    def __eq__(self, other):
        if not isinstance(other, Container):
            return False
        return self.name == other.name and self.contents == other.contents and \
            self.volume == other.volume and self.max_volume == other.max_volume

    def __hash__(self):
        return hash((self.name, self.volume, self.max_volume, *tuple(map(tuple, self.contents.items()))))

    def _self_add(self, source: Substance, how_much: str):
        # Only to be used in constructor and immediately after copy
        if not isinstance(source, Substance):
            raise TypeError("Invalid source type.")
        if how_much.endswith('M') and not source.is_solid():
            # TODO: molarity from liquids?
            raise ValueError("Molarity solutions can only be made from solids.")
        amount_to_transfer = round(Unit.convert_to_unit_value(source, how_much, self.volume), INTERNAL_PRECISION)
        self.contents[source] = round(self.contents.get(source, 0) + amount_to_transfer, INTERNAL_PRECISION)
        if source.is_liquid():
            self.volume = round(self.volume + amount_to_transfer, INTERNAL_PRECISION)
        if self.volume > self.max_volume:
            raise ValueError("Exceeded maximum volume")

    def _transfer(self, source_container: Container, volume: str):
        """ transfer from container to self """
        if not isinstance(source_container, Container):
            raise TypeError("Invalid source type.")
        volume_to_transfer, unit = Unit.extract_value_unit(volume)
        volume_to_transfer *= 1000.0  # convert L to mL
        volume_to_transfer = round(volume_to_transfer, INTERNAL_PRECISION)
        if unit != 'L':
            raise ValueError("We can only transfer liquid from other containers.")
        if volume_to_transfer > source_container.volume:
            raise ValueError("Not enough mixture left in source container." +
                             f" {volume_to_transfer} mL  needed of {source_container.name}" +
                             f" out of {source_container.volume} mL.")
        source_container, to = source_container.copy(), self.copy()
        ratio = volume_to_transfer / source_container.volume
        for substance, amount in source_container.contents.items():
            to.contents[substance] = round(to.contents.get(substance, 0) + amount * ratio, INTERNAL_PRECISION)
            source_container.contents[substance] = round(source_container.contents[substance] - amount * ratio,
                                                         INTERNAL_PRECISION)
        to.volume = round(to.volume + volume_to_transfer, INTERNAL_PRECISION)
        if to.volume > to.max_volume:
            raise ValueError("Exceeded maximum volume")
        source_container.volume = round(source_container.volume - volume_to_transfer, INTERNAL_PRECISION)
        return source_container, to

    def _transfer_slice(self, source_slice, volume):
        """ transfer from slice to self """

        def helper_func(elem):
            elem, to_array[0] = Container.transfer(elem, to_array[0], volume)
            return elem

        if isinstance(source_slice, Plate):
            source_slice = source_slice[:]
        if not isinstance(source_slice, PlateSlicer):
            raise TypeError("Invalid source type.")
        to = self.copy()
        source_slice = source_slice.copy()
        source_slice.plate = source_slice.plate.copy()
        volume_to_transfer, unit = extract_value_unit(volume)
        volume_to_transfer *= 1000.0  # convert L to mL
        volume_to_transfer = round(volume_to_transfer, INTERNAL_PRECISION)
        if unit != 'L':
            raise ValueError("We can only transfer liquid from other containers.")
        if source_slice.get().size * volume_to_transfer > (to.max_volume - to.volume):
            raise ValueError("Not enough room left in destination container.")

        to_array = [to]
        result = numpy.vectorize(helper_func, cache=True)(source_slice.get())
        source_slice.set(result)
        return source_slice.plate, to_array[0]

    def __repr__(self):
        return f"Container ({self.name}) ({self.volume}" + \
            f"{('/' + str(self.max_volume)) if self.max_volume != float('inf') else ''}) of ({self.contents})"

    @staticmethod
    def add(source: Substance, destination: Container, how_much):
        if not isinstance(destination, Container):
            raise TypeError("You can only use Container.add to add to a Container")
        destination = destination.copy()
        destination._self_add(source, how_much)
        return destination

    @staticmethod
    def transfer(source, destination: Container, volume):
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
            container = container.add(what, container, f"{round(moles_to_add, INTERNAL_PRECISION)} mol")
        else:  # Liquid
            volume_to_add = round(moles_to_add * what.mol_weight / (what.density * 1000), EXTERNAL_PRECISION)
            container = container.add(solvent, container, f"{volume - volume_to_add} mL")
            container = container.add(what, container, f"{volume_to_add} mL")
        return container


class Plate:
    def __init__(self, name, max_volume_per_well, make="generic", rows=8, columns=12):
        """
            Creates a generic plate.

            Attributes:
                name (str): name of plate
                max_volume_per_well (float): maximum volume of each well in uL
                make (str): name of this kind of plate
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
            self.max_volume_per_well = max_volume_per_well / 1000  # store in mL
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

        self.wells = numpy.array([[Container(f"well {row + 1},{col + 1}", max_volume=self.max_volume_per_well)
                                   for col in range(self.n_columns)] for row in range(self.n_rows)])

    def __getitem__(self, item) -> PlateSlicer:
        return PlateSlicer(self, item)

    def __repr__(self):
        return f"Plate: {self.name}"

    def volumes(self, substance=None):
        if substance is None:
            return numpy.vectorize(lambda x: x.volume)(self.wells)
        else:
            def helper(elem):
                if substance.is_liquid() and substance in elem.contents:
                    return round(elem.contents[substance], EXTERNAL_PRECISION)
                else:
                    return 0

            return numpy.vectorize(helper)(self.wells)

    def substances(self):
        substances_arr = numpy.vectorize(lambda elem: elem.contents.keys())(self.wells)
        return set.union(*map(set, substances_arr.flatten()))

    def moles(self, substance):
        def helper(elem):
            if substance not in elem.contents:
                return 0
            if substance.is_liquid():
                return round(elem.contents[substance] * substance.density / substance.mol_weight, EXTERNAL_PRECISION)
            elif substance.is_solid():
                return round(elem.contents[substance], EXTERNAL_PRECISION)

        return numpy.vectorize(helper, cache=True)(self.wells)

    def volume(self):
        return self.volumes().sum()

    def copy(self):
        new_plate = Plate(self.name, self.max_volume_per_well, self.make, 1, 1)
        new_plate.n_rows, new_plate.n_columns = self.n_rows, self.n_columns
        new_plate.row_names, new_plate.column_names = self.row_names, self.column_names
        new_plate.wells = self.wells.copy()
        return new_plate

    @staticmethod
    def add(source: Substance, destination: Plate | PlateSlicer, how_much):
        if not isinstance(destination, (Plate, PlateSlicer)):
            raise TypeError("You can only use Plate.add to add to a Plate")
        if isinstance(destination, Plate):
            destination = destination[:]
        return PlateSlicer._add(source, destination, how_much)

    @staticmethod
    def transfer(source, destination: Plate | PlateSlicer, volume):
        if not isinstance(destination, (Plate, PlateSlicer)):
            raise TypeError("You can only use Plate.transfer into a Plate")
        return PlateSlicer._transfer(source, destination, volume)


class Recipe:
    def __init__(self):
        self.indexes = dict()
        self.results = []
        self.steps = []
        self.locked = False

    def uses(self, *args):
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

    def transfer(self, source, destination, how_much):
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
        self.steps.append(('transfer', source, destination, how_much))
        return self

    def create_container(self, name, max_volume, initial_contents=None):
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
        if self.locked:
            raise RuntimeError("This recipe is locked.")
        new_container = Container("{what.name} {concentration:.2}M", max_volume=volume)
        self.uses(new_container)
        self.steps.append(('stock', new_container, what, concentration, solvent, volume))
        return new_container

    def bake(self):
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

            elif operation == 'transfer':
                frm, to, how_much = rest
                # used items can change in a recipe
                frm_index = self.indexes[frm] if not isinstance(frm, PlateSlicer) else self.indexes[frm.plate]
                to_index = self.indexes[to] if not isinstance(to, PlateSlicer) else self.indexes[to.plate]

                # containers and such can change while building the recipe

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

                # TODO: ?
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
                self.results[to_index] = Container.create_stock_solution(what, concentration, solvent, volume)

        self.locked = True
        return [result for result in self.results if not isinstance(result, Substance)]


class PlateSlicer(Slicer):
    def __init__(self, plate, item):
        self.plate = plate
        super().__init__(plate.wells, plate.row_names, plate.column_names, item)

    @property
    def array(self):
        return self.plate.wells

    @array.setter
    def array(self, array):
        self.plate.wells = array

    def copy(self):
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
                elem, to_array[0] = to_array[0].transfer(elem, how_much)
                return elem

            to_array = [to.get()]
            frm.set(numpy.vectorize(helper_func, cache=True)(frm.get()))
            to.set(to_array[0])

        elif frm.size == to.size and frm.shape == to.shape:
            def helper(elem1, elem2):
                return Container.transfer(elem1, elem2, how_much)

            func = numpy.frompyfunc(helper, 2, 2)
            frm_result, to_result = func(frm.get(), to.get())
            frm.set(frm_result)
            to.set(to_result)
        else:
            raise ValueError("Source and destination slices must be the same size and shape.")

        return frm.plate, to.plate
