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

    # def set(self, values):
    #     super().set(values)
    #     pl

    def add(self, frm, how_much):
        self.set(numpy.vectorize(lambda elem: elem.transfer(frm, how_much), cache=True)(self.get()))
        return self.plate

    def transfer(self, frm, how_much):
        def helper_func(elem):
            frm_array[0], elem = elem.transfer(frm_array[0], how_much)
            return elem

        frm_array = [frm]
        result = numpy.vectorize(helper_func, cache=True)(self.get())
        if isinstance(self.get(), Container):  # A zero-dim array was returned.
            result = result.item()
        self.set(result)
        # TODO: investigate why this is necessary.
        return frm_array[0], self.plate

    def transfer_slice(self, frm, how_much):
        self.plate = self.plate.copy()
        frm.plate = frm.plate.copy()
        if frm.size == 1:
            # Source from the single element in frm
            if frm.shape != ():
                raise RuntimeError("Shape of source should have been ()")

            def helper_func(elem):
                frm_array[0], elem = elem.transfer(frm_array[0], how_much)
                return elem

            frm_array = [frm.get()]
            # self.set(numpy.vectorize(helper_func, cache=True)(self.get()))
            result = numpy.vectorize(helper_func, cache=True)(self.get())
            self.set(result)
            # self.data.wells = self.array
            frm.set(frm_array[0])
            # frm.data.wells = frm.array

        elif self.size == 1:
            #  Replace the single element in self
            if self.shape != ():
                raise RuntimeError("Shape of source should have been ()")

            def helper_func(elem):
                elem, to_array[0] = to_array[0].transfer(elem, how_much)
                return elem

            to_array = [self.get()]
            frm.set(numpy.vectorize(helper_func, cache=True)(frm.get()))
            # frm.data.wells = frm.array
            self.set(to_array[0])
            # to.data.wells = to.array

        elif frm.size == self.size and frm.shape == self.shape:
            def helper(elem1, elem2):
                elem1, elem2 = elem2.transfer(elem1, how_much)
                return elem1, elem2

            func = numpy.frompyfunc(helper, 2, 2)
            frm_result, to_result = func(frm.get(), self.get())
            frm.set(frm_result)
            # frm.data.wells = frm.array
            self.set(to_result)
            # to.data.wells = to.array
        else:
            raise ValueError("Source and destination slices must be the same size and shape.")

        return frm.plate, self.plate


# def _slicer_add(frm, to, how_much):
#     to.set(numpy.vectorize(lambda elem: elem.transfer(frm, how_much), cache=True)(to.get()))
#     return to
#
#
# Slicer.add = lambda self, frm, how_much: _slicer_add(frm, self, how_much)
#
#
# def _slicer_transfer(frm, to, how_much):
#     def helper_func(elem):
#         frm_array[0], elem = elem.transfer(frm_array[0], how_much)
#         return elem
#
#     frm_array = [frm]
#     result = numpy.vectorize(helper_func, cache=True)(to.get())
#     if isinstance(to.get(), Container):  # A zero-dim array was returned.
#         result = result.item()
#     to.set(result)
#     # TODO: investigate why this is necessary.
#     to.data.wells = to.array
#     return frm_array[0], to.data
#
#
# Slicer.transfer = lambda self, frm, how_much: _slicer_transfer(frm, self, how_much)
#
#
# def _slicer_transfer_slices(frm, to, how_much):
#     if frm.size == 1:
#         # Source from the single element in frm
#         if frm.shape != ():
#             raise RuntimeError("Shape of source should have been ()")
#
#         def helper_func(elem):
#             frm_array[0], elem = elem.transfer(frm_array[0], how_much)
#             return elem
#
#         frm_array = [frm.get()]
#         to.set(numpy.vectorize(helper_func, cache=True)(to.get()))
#         to.data.wells = to.array
#         frm.set(frm_array[0])
#         frm.data.wells = frm.array
#
#     elif to.size == 1:
#         #  Replace the single element in to
#         if to.shape != ():
#             raise RuntimeError("Shape of source should have been ()")
#
#         def helper_func(elem):
#             elem, to_array[0] = to_array[0].transfer(elem, how_much)
#             return elem
#
#         to_array = [to.get()]
#         frm.set(numpy.vectorize(helper_func, cache=True)(frm.get()))
#         frm.data.wells = frm.array
#         to.set(to_array[0])
#         to.data.wells = to.array
#
#     elif frm.size == to.size and frm.shape == to.shape:
#         def helper(elem1, elem2):
#             elem1, elem2 = elem2.transfer(elem1, how_much)
#             return elem1, elem2
#
#         func = numpy.frompyfunc(helper, 2, 2)
#         frm_result, to_result = func(frm.get(), to.get())
#         frm.set(frm_result)
#         frm.data.wells = frm.array
#         to.set(to_result)
#         to.data.wells = to.array
#     else:
#         raise ValueError("Source and destination slices must be the same size and shape.")
#     return frm.data, to.data
#
#
# Slicer.transfer_slice = lambda self, frm, how_much: _slicer_transfer_slices(frm, self, how_much)


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

    def _self_add(self, frm: Substance, how_much: str):
        # Only to be used in constructor and immediately after copy
        if not isinstance(frm, Substance):
            return TypeError("Invalid source type.")
        if how_much.endswith('M') and frm.type != Substance.SOLID:
            # TODO: molarity from liquids?
            raise ValueError("Molarity solutions can only be made from solids.")
        volume_to_transfer = round(frm.convert_to_unit_value(how_much, self.volume), 10)
        self.contents[frm] = round(self.contents.get(frm, 0) + volume_to_transfer, 10)
        if frm.type == Substance.LIQUID:
            self.volume = round(self.volume + volume_to_transfer, 10)
            # to.volume += volume_to_transfer
        if self.volume > self.max_volume:
            raise ValueError("Exceeded maximum volume")

    def add(self, frm: Substance, how_much: str):
        to = self.copy()
        to._self_add(frm, how_much)
        return to

    def transfer(self, frm: Container, how_much: str):
        if not isinstance(frm, Container):
            return TypeError("Invalid source type.")
        volume_to_transfer, unit = extract_value_unit(how_much)
        volume_to_transfer *= 1000.0  # convert L to mL
        volume_to_transfer = round(volume_to_transfer, 10)
        if unit != 'L':
            raise ValueError("We can only transfer liquid from other containers.")
        if volume_to_transfer > frm.volume:
            raise ValueError("Not enough mixture left in source container." + f"{frm} ({how_much}) -> {self}")
        frm, to = frm.copy(), self.copy()
        ratio = volume_to_transfer / frm.volume
        for substance, amount in frm.contents.items():
            to.contents[substance] = round(to.contents.get(substance, 0) + amount * ratio, 10)
            frm.contents[substance] = round(frm.contents[substance] - amount * ratio, 10)
        to.volume = round(to.volume + volume_to_transfer, 10)
        if to.volume > to.max_volume:
            raise ValueError("Exceeded maximum volume")
        # frm.volume -= volume_to_transfer
        frm.volume = round(frm.volume - volume_to_transfer, 10)
        return frm, to

    def __repr__(self):
        return f"Container ({self.name}) ({self.volume}" + \
            f"{('/' + str(self.max_volume)) if self.max_volume != float('inf') else ''}) of ({self.contents})"


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

    def __getitem__(self, item):
        return PlateSlicer(self, item)
        # slicer = Slicer(self, self.wells, self.row_names, self.column_names, item)
        # slicer.transfer_slice = lambda frm, how_much: _slicer_transfer_slices(frm, slicer, how_much)
        # return slicer

    def __repr__(self):
        return f"Plate: {self.name}"

    def volumes(self, arr=None):
        if arr is None:
            arr = self.wells
        elif isinstance(arr, Slicer):
            arr = arr.get()
        return numpy.vectorize(lambda x: x.volume)(arr)

    def substances(self, arr=None):
        if arr is None:
            arr = self.wells
        elif isinstance(arr, Slicer):
            arr = arr.get()
        substances_arr = numpy.vectorize(lambda elem: elem.contents.keys())(arr)
        return set.union(*map(set, substances_arr.flatten()))

    def moles(self, substance, arr=None):
        PRECISION = 6
        if arr is None:
            arr = self.wells
        elif isinstance(arr, Slicer):
            arr = arr.get()

        def helper(elem):
            if substance not in elem.contents:
                return 0
            if substance.type == Substance.LIQUID:
                return round(elem.contents[substance] * substance.density / substance.mol_weight, PRECISION)
            elif substance.type == Substance.SOLID:
                return round(elem.contents[substance], PRECISION)

        return numpy.vectorize(helper, cache=True)(arr)

    def copy(self):
        new_plate = Plate(self.name, self.make, 1, 1, self.max_volume_per_well)
        new_plate.n_rows, new_plate.n_columns = self.n_rows, self.n_columns
        new_plate.row_names, new_plate.column_names = self.row_names, self.column_names
        new_plate.wells = self.wells.copy()
        return new_plate


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
        if not isinstance(to, (Container, Plate, Slicer)):
            raise ValueError("Invalid destination type.")
        if not isinstance(frm, (Substance, Container, Slicer)):
            raise ValueError("Invalid source type.")
        if (frm.data if isinstance(frm, Slicer) else frm) not in self.indexes:
            raise ValueError("Source not found in declared uses.")
        if (to.data if isinstance(to, Slicer) else to) not in self.indexes:
            raise ValueError("Destination not found in declared uses.")
        self.steps.append((frm, to, how_much))
        return self

    def create_container(self, name, max_volume, initial_contents=None):
        new_container = Container(name, max_volume)
        self.uses(new_container)
        if initial_contents:
            for substance, how_much in initial_contents:
                if not isinstance(substance, Substance):
                    raise ValueError("Containers can only be created from substances.")
                self.steps.append((substance, new_container, how_much))
        return new_container

    def build(self):

        for frm, to, how_much in self.steps:
            frm_index = self.indexes[frm] if not isinstance(frm, Slicer) else self.indexes[frm.data]
            to_index = self.indexes[to] if not isinstance(to, Slicer) else self.indexes[to.data]

            # containers and such can change while building the recipe

            if isinstance(frm, Slicer):
                new_frm = frm.copy()
                new_frm.transfer_slice = frm.transfer_slice
                new_frm.data = self.results[frm_index]
                frm = new_frm
            else:
                frm = self.results[frm_index]

            if isinstance(to, Slicer):
                new_to = to.copy()
                new_to.data = self.results[to_index]
                to = new_to
            else:
                to = self.results[to_index]

            # # # used items can change in a recipe
            #
            # if isinstance(frm, Plate):
            #     frm = frm[:]
            # if isinstance(to, Plate):
            #     to = to[:]
            #
            # # frm is a Substance, Container, or Slicer
            # # to is a Container or Slicer
            # # Six combinations
            #
            # if isinstance(to, Container):
            #     if isinstance(frm, Substance):
            #         to = to.add(frm, how_much)
            #     elif isinstance(frm, Container):
            #         frm, to = to.transfer(frm, how_much)
            #     else:  # frm == Slicer
            #         # TODO: Is this something we want to work?
            #         pass
            # elif isinstance(to, Slicer):
            #     if isinstance(frm, Substance):
            #         ds
            #     elif isinstance(frm, Container):
            #         frm_array = [frm]
            #         helper_function = helper_factory(frm_array, how_much)
            #         result = numpy.vectorize(helper_function, cache=True)(to.get())
            #         if isinstance(to.get(), Container):  # A zero-dim array was returned.
            #             result = result.item()
            #         to.set(result)
            #         # TODO: investigate why this is necessary.
            #         to.data.wells = to.array
            #         frm = frm_array[0]
            #     elif isinstance(frm, Slicer):
            #         if frm.size == 1:
            #             # Source from the single element in frm
            #             if frm.shape != (1,):
            #                 raise RuntimeError("Shape of source should have been (1,)")
            #
            #             frm_array = [frm.get()[0]]
            #             helper_function = helper_factory(frm_array, how_much)
            #             to.set(numpy.vectorize(helper_function, cache=True)(to.get()))
            #             to.data.wells = to.array
            #             frm.get()[0] = frm_array[0]
            #         elif to.size == 1:
            #             #  Replace the single element in to
            #             if to.shape != (1,):
            #                 raise RuntimeError("Shape of source should have been (1,)")
            #             to_array = [to.get()[0]]
            #
            #             def to_helper(elem):
            #                 elem, to_array[0] = to_array[0].transfer(elem, how_much)
            #
            #             frm.set(numpy.vectorize(to_helper, cache=True)(frm.get()))
            #             to.data.wells = to.array
            #             to.get()[0] = to_array[0]
            #         elif frm.size == to.size and frm.shape == to.shape:
            #             func = numpy.frompyfunc(lambda elem1, elem2: elem2.transfer(elem1, how_much), 2, 2)
            #             frm_result, to_result = func(frm.get(), to.get())
            #             frm.set(frm_result)
            #             frm.data.wells = frm.array
            #             to.set(frm_result)
            #             to.data.wells = to.array
            #         else:
            #             raise ValueError("Source and destination slices must be the same size and shape.")
            if isinstance(frm, Substance):
                to = to.add(frm, how_much)
            elif isinstance(frm, Container):
                frm, to = to.transfer(frm, how_much)
            elif isinstance(frm, Slicer):
                frm, to = to.transfer_slice(frm, how_much)

            self.results[frm_index] = frm
            self.results[to_index] = to
            # self.results[frm_index] = frm.data if isinstance(frm, Slicer) else frm
            # self.results[to_index] = to.data if isinstance(to, Slicer) else to

        return [result for result in self.results if not isinstance(result, Substance)]
