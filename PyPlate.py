# Allow typing reference while still building classes
from __future__ import annotations
import re
import string
from typing import Tuple, Dict
import numpy


def convert_prefix(prefix):
    prefixes = {'µ': 1e-6, 'm': 1e-3, 'c': 1e-2, 'd': 1e-1, '': 1, 'k': 1e3, 'M': 1e6}
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

    next_id = 0

    def __init__(self, name, mol_type):
        self.id = Substance.next_id
        Substance.next_id += 1
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
        |LIQUID  |   Yes  |   Yes  |   Yes  |   No   |   No   |   mL   |
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
            elif unit == 'M':   # molar
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
    def __init__(self, name, max_volume=float('inf')):
        self.name = name
        self.contents: Dict[Substance, float] = dict()
        self.volume = 0.0
        self.max_volume = max_volume

    def copy(self):
        new_container = Container(self.name, self.max_volume)
        new_container.contents = self.contents.copy()
        new_container.volume = self.volume
        return new_container

    def transfer_substance(self, frm: Substance, how_much: str):
        if how_much.endswith('M') and frm.type != Substance.SOLID:
            # TODO: molarity from liquids?
            raise ValueError("Molarity solutions can only be made from solids.")
        volume_to_transfer = frm.convert_to_unit_value(how_much, self.volume)
        to = self.copy()
        to.contents[frm] = to.contents.get(frm, 0) + volume_to_transfer
        if frm.type == Substance.LIQUID:
            to.volume += volume_to_transfer
        if to.volume > to.max_volume:
            raise ValueError("Exceeded maximum volume")
        return to

    def transfer_container(self, frm: Container, how_much: str):
        volume_to_transfer, unit = extract_value_unit(how_much)
        volume_to_transfer *= 1000.0    # convert to mL
        if unit != 'L':
            raise ValueError("We can only transfer liquid from other containers.")
        if volume_to_transfer > frm.volume:
            raise ValueError("Not enough mixture left in source container.")
        frm, to = frm.copy(), self.copy()
        ratio = volume_to_transfer / frm.volume
        for substance, amount in frm.contents.items():
            to.contents[substance] = to.contents.get(substance, 0) + amount * ratio
            frm.contents[substance] -= amount * ratio
        to.volume += volume_to_transfer
        if to.volume > to.max_volume:
            raise ValueError("Exceeded maximum volume")
        frm.volume -= volume_to_transfer
        return frm, to

    def transfer(self, frm, how_much: str):
        if isinstance(frm, Substance):
            return self.transfer_substance(frm, how_much)
        elif isinstance(frm, Container):
            return self.transfer_container(frm, how_much)
        raise TypeError("Invalid source type.")

    def __repr__(self):
        return f"Container ({self.name}) ({self.volume}" +\
            f"{('/'+str(self.max_volume)) if self.max_volume != float('inf') else ''}) of ({self.contents})"


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
            self.row_names = [f"{i+1}" for i in range(rows)]
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
            self.max_volume_per_well = max_volume_per_well / 1000   # store in mL
        except (ValueError, OverflowError):
            raise ValueError(f"invalid max volume per well {max_volume_per_well}")

        if isinstance(columns, int):
            if columns < 1:
                raise ValueError("illegal number of columns")
            self.n_columns = columns
            self.column_names = [f"{i+1}" for i in range(columns)]
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

        self.wells = numpy.array([[Container(f"well {col+1},{row+1}", max_volume=self.max_volume_per_well)
                                   for col in range(self.n_columns)] for row in range(self.n_rows)])


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
                self.results.append(arg)

    def transfer(self, frm, to, how_much):
        if not isinstance(to, Container):
            raise ValueError("Invalid destination type.")
        if not isinstance(frm, (Substance, Container)):
            raise ValueError("Invalid source type.")
        if frm not in self.indexes:
            raise ValueError("Source not found in uses.")
        if to not in self.indexes:
            raise ValueError("Destination not found in uses.")
        self.steps.append((frm, to, how_much))
        return self

    def build(self):
        for frm, to, how_much in self.steps:
            frm_index, to_index = self.indexes[frm], self.indexes[to]

            # used items can change in a recipe
            frm = self.results[frm_index]
            to: Container = self.results[to_index]

            if isinstance(frm, Substance):
                to = to.transfer(frm, how_much)
            elif isinstance(frm, Container):
                frm, to = to.transfer(frm, how_much)
            self.results[frm_index] = frm
            self.results[to_index] = to
        return self.results
