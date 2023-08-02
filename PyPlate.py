# Allow typing reference while still building classes
from __future__ import annotations
import re
import string
from typing import Tuple, Dict
import numpy
from Slicer import Slicer


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

    def _add(self, frm, how_much):
        to = self.copy()
        to.plate = to.plate.copy()
        result = numpy.vectorize(lambda elem: Container.add(frm, elem, how_much), cache=True)(to.get())
        to.set(result)
        return to.plate

    def _transfer(self, frm, how_much):
        to = self.copy()
        to.plate = self.plate.copy()

        def helper_func(elem):
            # frm_array[0], elem = elem._transfer(frm_array[0], how_much)
            frm_array[0], elem = Container.transfer(frm_array[0], elem, how_much)
            return elem

        frm_array = [frm]
        result = numpy.vectorize(helper_func, cache=True)(to.get())
        if isinstance(to.get(), Container):  # A zero-dim array was returned.
            result = result.item()
        to.set(result)
        return frm_array[0], to.plate

    def _transfer_slice(self, frm, how_much):

        to = self.copy()
        frm = frm.copy()

        if self.plate != frm.plate:
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

        elif self.size == 1:
            #  Replace the single element in self
            if self.shape != ():
                raise RuntimeError("Shape of source should have been ()")

            def helper_func(elem):
                elem, to_array[0] = to_array[0].transfer(elem, how_much)
                return elem

            to_array = [to.get()]
            frm.set(numpy.vectorize(helper_func, cache=True)(frm.get()))
            to.set(to_array[0])

        elif frm.size == self.size and frm.shape == self.shape:
            def helper(elem1, elem2):
                return Container.transfer(elem1, elem2, how_much)

            func = numpy.frompyfunc(helper, 2, 2)
            frm_result, to_result = func(frm.get(), to.get())
            frm.set(frm_result)
            to.set(to_result)
        else:
            raise ValueError("Source and destination slices must be the same size and shape.")

        return frm.plate, to.plate


def convert_prefix(prefix):
    prefixes = {'u': 1e-6, 'µ': 1e-6, 'm': 1e-3, 'c': 1e-2, 'd': 1e-1, '': 1, 'k': 1e3, 'M': 1e6}
    if prefix in prefixes:
        return prefixes[prefix]
    raise ValueError(f"Invalid prefix: {prefix}")


def extract_value_unit(s: str) -> Tuple[float, str]:
    if not isinstance(s, str):
        raise TypeError
    # (floating point number in 1.0e1 format) possibly some white space (alpha string)
    match = re.fullmatch(r"(\d+(?:\.\d+)?(?:e-?\d+)?)\s*([a-zA-Z]+)", s)
    if not match:
        raise ValueError("Invalid quantity.")
    value, unit = match.groups()
    value = float(value)
    if unit == 'AU':
        return value, unit
    for base_unit in {'mol', 'g', 'L', 'M'}:
        if unit.endswith(base_unit):
            prefix = unit[:-len(base_unit)]
            value = value * convert_prefix(prefix)
            return value, base_unit
    raise ValueError("Invalid unit.")


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

    def __init__(self, name, mol_type):
        self.name = name
        self.type = mol_type
        self.mol_weight = self.density = self.concentration = None

    def __repr__(self):
        if self.type == Substance.SOLID:
            return f"SOLID ({self.name}: {self.mol_weight})"
        if self.type == Substance.LIQUID:
            return f"LIQUID ({self.name}: {self.mol_weight}, {self.density})"
        else:
            return f"ENZYME ({self.name})"

    def __eq__(self, other):
        if not isinstance(other, Substance):
            return False
        return self.name == other.name and self.type == other.type and self.mol_weight == other.mol_weight\
            and self.density == other.density and self.concentration == other.concentration

    def __hash__(self):
        return hash((self.name, self.type, self.mol_weight, self.density, self.concentration))

    @staticmethod
    def solid(name, mol_weight):
        substance = Substance(name, Substance.SOLID)
        substance.mol_weight = mol_weight
        return substance

    @staticmethod
    def liquid(name, mol_weight, density):
        substance = Substance(name, Substance.LIQUID)
        substance.mol_weight = mol_weight  # g / mol
        substance.density = density  # g / mL
        substance.concentration = 1000.0 * density / mol_weight  # mol / L
        return substance

    @staticmethod
    def enzyme(name):
        return Substance(name, Substance.ENZYME)

    def convert_to_unit_value(self, how_much: str, volume: float = 0.0):  # mol, mL or AU
        """
        @private
        Converts amount to standard units.

        :param how_much: Amount of substance to convert
        :param volume: Volume of containing Mixture in mL
        :return: float

                 +--------+--------+--------+--------+--------+--------+
                 |              Valid Input                   | Output |
                 |    g   |    L   |   mol  |    M   |    AU  |        |
        +--------+--------+--------+--------+--------+--------+--------+
        |SOLID   |   Yes  |   No   |   Yes  |   Yes  |   No   |   mol  |
        +--------+--------+--------+--------+--------+--------+--------+
        |LIQUID  |   Yes  |   Yes  |   Yes  |   ??   |   No   |   mL   |
        +--------+--------+--------+--------+--------+--------+--------+
        |ENZYME  |   No   |   No   |   No   |   No   |   Yes  |   AU   |
        +--------+--------+--------+--------+--------+--------+--------+
        """

        value, unit = extract_value_unit(how_much)
        if self.type == Substance.SOLID:  # Convert to moles
            if unit == 'g':  # mass
                return value / self.mol_weight
            elif unit == 'mol':  # moles
                return value
            elif unit == 'M':  # molar
                if volume <= 0.0:
                    raise ValueError('Must have a liquid to add a molar concentration.')
                # value = molar concentration in mol/L, volume = volume in mL
                return value * volume / 1000
            raise ValueError("We only measure solids in grams and moles.")
        elif self.type == Substance.LIQUID:  # Convert to mL
            if unit == 'g':  # mass
                return value / self.density
            elif unit == 'L':  # volume
                return value * 1000  # mL
            elif unit == 'mol':  # moles
                return (value / self.concentration) / 1000.0
            raise ValueError
        elif self.type == Substance.ENZYME:
            if unit == 'AU':
                return value
            raise ValueError


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
        return self.name == other.name and self.contents == other.contents and\
            self.volume == other.volume and self.max_volume == other.max_volume

    def __hash__(self):
        return hash((self.name, self.volume, self.max_volume, *tuple(map(tuple, self.contents.items()))))

    def _self_add(self, source: Substance, how_much: str):
        # Only to be used in constructor and immediately after copy
        if not isinstance(source, Substance):
            raise TypeError("Invalid source type.")
        if how_much.endswith('M') and source.type != Substance.SOLID:
            # TODO: molarity from liquids?
            raise ValueError("Molarity solutions can only be made from solids.")
        amount_to_transfer = round(source.convert_to_unit_value(how_much, self.volume), 10)
        self.contents[source] = round(self.contents.get(source, 0) + amount_to_transfer, 10)
        if source.type == Substance.LIQUID:
            self.volume = round(self.volume + amount_to_transfer, 10)
        if self.volume > self.max_volume:
            raise ValueError("Exceeded maximum volume")

    def _add(self, source: Substance, how_much: str):
        """ add substance to self """
        to = self.copy()
        to._self_add(source, how_much)
        return to

    def _transfer(self, source_container: Container, volume: str):
        """ transfer from container to self """
        if not isinstance(source_container, Container):
            raise TypeError("Invalid source type.")
        volume_to_transfer, unit = extract_value_unit(volume)
        volume_to_transfer *= 1000.0  # convert L to mL
        volume_to_transfer = round(volume_to_transfer, 10)
        if unit != 'L':
            raise ValueError("We can only transfer liquid from other containers.")
        if volume_to_transfer > source_container.volume:
            raise ValueError("Not enough mixture left in source container." +
                             f"{source_container} ({volume}) -> {self}")
        source_container, to = source_container.copy(), self.copy()
        ratio = volume_to_transfer / source_container.volume
        for substance, amount in source_container.contents.items():
            to.contents[substance] = round(to.contents.get(substance, 0) + amount * ratio, 10)
            source_container.contents[substance] = round(source_container.contents[substance] - amount * ratio, 10)
        to.volume = round(to.volume + volume_to_transfer, 10)
        if to.volume > to.max_volume:
            raise ValueError("Exceeded maximum volume")
        source_container.volume = round(source_container.volume - volume_to_transfer, 10)
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
        volume_to_transfer = round(volume_to_transfer, 10)
        if unit != 'L':
            raise ValueError("We can only transfer liquid from other containers.")
        if source_slice.get().size * volume_to_transfer > (to.max_volume - to.volume):
            raise ValueError("Not enough room left in destination container.")

        to_array = [to]
        result = numpy.vectorize(helper_func, cache=True)(source_slice.get())
        source_slice.set(result)
        return source_slice.plate, to_array[0]

    def __repr__(self):
        return f"Container ({self.name}) ({self.volume}" +\
            f"{('/' + str(self.max_volume)) if self.max_volume != float('inf') else ''}) of ({self.contents})"

    @staticmethod
    def add(source: Substance, destination: Container, how_much):
        if not isinstance(destination, Container):
            raise TypeError("You can only use Container.add to add to a Container")
        return destination._add(source, how_much)

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


class Plate:
    def __init__(self, name, make, rows, columns, max_volume_per_well):
        """
            Creates a generic plate.

            Attributes:
                name (str): name of plate
                make (str): name of this kind of plate
                rows (int or list): number of rows or list of names of rows
                columns (int or list): number of columns or list of names of columns
                max_volume_per_well (float): maximum volume of each well in uL
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
            self.row_names = [f"{i + 1}" for i in range(rows)]
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

    def volumes(self, arr=None):
        if arr is None:
            arr = self.wells
        elif isinstance(arr, PlateSlicer):
            arr = arr.get()
        return numpy.vectorize(lambda x: x.volume)(arr)

    def substances(self, arr=None):
        if arr is None:
            arr = self.wells
        elif isinstance(arr, PlateSlicer):
            arr = arr.get()
        substances_arr = numpy.vectorize(lambda elem: elem.contents.keys())(arr)
        return set.union(*map(set, substances_arr.flatten()))

    def moles(self, substance, arr=None):
        PRECISION = 6
        if arr is None:
            arr = self.wells
        elif isinstance(arr, PlateSlicer):
            arr = arr.get()

        def helper(elem):
            if substance not in elem.contents:
                return 0
            if substance.type == Substance.LIQUID:
                return round(elem.contents[substance] * substance.density / substance.mol_weight, PRECISION)
            elif substance.type == Substance.SOLID:
                return round(elem.contents[substance], PRECISION)

        return numpy.vectorize(helper, cache=True)(arr)

    def volume(self, arr=None):
        return numpy.sum(self.volumes(arr))

    def copy(self):
        new_plate = Plate(self.name, self.make, 1, 1, self.max_volume_per_well)
        new_plate.n_rows, new_plate.n_columns = self.n_rows, self.n_columns
        new_plate.row_names, new_plate.column_names = self.row_names, self.column_names
        new_plate.wells = self.wells.copy()
        return new_plate

    def _add(self, source: Substance, how_much):
        return self[:]._add(source, how_much)

    def _transfer(self, source_container: Container, volume):
        return self[:]._transfer(source_container, volume)

    def _transfer_slice(self, source_slice, volume):
        return self[:]._transfer_slice(source_slice, volume)

    @staticmethod
    def add(source: Substance, destination: Plate | PlateSlicer, how_much):
        if not isinstance(destination, (Plate, PlateSlicer)):
            raise TypeError("You can only use Plate.add to add to a Plate")
        return destination._add(source, how_much)

    @staticmethod
    def transfer(source, destination: Plate | PlateSlicer, volume):
        if not isinstance(destination, (Plate, PlateSlicer)):
            raise TypeError("You can only use Plate.transfer into a Plate")
        if isinstance(source, Container):
            return destination._transfer(source, volume)
        elif isinstance(source, (Plate, PlateSlicer)):
            return destination._transfer_slice(source, volume)
        else:
            raise TypeError("Invalid source type.")


class Generic96WellPlate(Plate):
    """
    Represents a 96 well plate.
    """

    def __init__(self, name, max_volume_per_well):
        make = "generic 96 well plate"
        rows = list(string.ascii_uppercase[:8])
        columns = 12
        super().__init__(name, make, rows, columns, max_volume_per_well)


class Recipe:
    def __init__(self):
        self.indexes = dict()
        self.results = []
        self.steps = []

    def uses(self, *args):
        for arg in args:
            if arg not in self.indexes:
                self.indexes[arg] = len(self.results)
                if isinstance(arg, Substance):
                    self.results.append(arg)
                else:
                    self.results.append(arg.copy())
        return self

    def transfer(self, frm, to, how_much):
        if not isinstance(to, (Container, Plate, PlateSlicer)):
            raise TypeError("Invalid destination type.")
        if not isinstance(frm, (Substance, Container, PlateSlicer)):
            raise TypeError("Invalid source type.")
        if (frm.plate if isinstance(frm, PlateSlicer) else frm) not in self.indexes:
            raise ValueError("Source not found in declared uses.")
        if (to.plate if isinstance(to, PlateSlicer) else to) not in self.indexes:
            raise ValueError("Destination not found in declared uses.")
        if isinstance(frm, Plate):
            frm = frm[:]
        if isinstance(to, Plate):
            to = to[:]
        self.steps.append(('transfer', frm, to, how_much))
        return self

    def create_container(self, name, max_volume, initial_contents=None):
        new_container = Container(name, max_volume)
        self.uses(new_container)
        if initial_contents:
            for substance, how_much in initial_contents:
                if not isinstance(substance, Substance):
                    raise ValueError("Containers can only be created from substances.")
                self.steps.append(('add', substance, new_container, how_much))
        return new_container

    def build(self):

        for operation, frm, to, how_much in self.steps:
            if operation == 'add':
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

                if isinstance(frm, Substance): # Adding a substance is handled differently
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

        return [result for result in self.results if not isinstance(result, Substance)]
