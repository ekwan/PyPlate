
# Allow typing reference while still building classes
from __future__ import annotations

from typing import Iterable, Tuple

from copy import deepcopy, copy

import numpy as np
import pandas
from pandas.io.formats.style import Styler

from pyplate.config import config
from pyplate.container import Container
from pyplate.slicer import Slicer
from pyplate.substance import Substance
from pyplate.unit import Unit


class Plate:
    """
    A spatially ordered collection of Containers, like a 96-well plate.
    The spatial arrangement must be rectangular. Immutable.
    """

    name: str
    make: str
    max_volume_per_well: float
    n_rows: int
    n_columns: int
    row_names: list[str]
    column_names: list[str]
    wells: np.ndarray[Container]

    def __init__(self, name: str, 
                 max_volume_per_well: str, 
                 make: str = "generic", 
                 rows: int | Iterable[str] = 8, 
                 columns: int | Iterable[str] = 12):
        """
            Creates a Plate object.

            Rows and columns may either be specified with an overall count or 
            with a set of names. If specified with an overall count, the rows 
            will be assigned letters as names (e.g. ['A', 'B', 'C', ...]), and 
            the columns will be assigned indices starting with 1 as names. 
            
            Each well is named with the format 'Well [ROW_NAME]_[COLUMN_NAME]. 
            E.g. if overall counts are provided for both rows and columns, the 
            first row of wells will be named 'Well A_1', 'Well A_2', 'Well A_3',
            etc. 

            Arguments:
                name (str): The name of plate.
                max_volume_per_well (str): The maximum volume of each well.
                make (str): The brand name or an equivalent descriptor for the 
                    type of plate. 
                rows (int | Iterable[str]): The number of rows or a set of row 
                    names.
                columns (int | Iterable[str]): The number of columns or a set of 
                    column names.
        """

        # Ensure name argument satisfies type and value pre-conditions
        if not isinstance(name, str):
            raise TypeError("Name must be a str.")
        if len(name) == 0:
            raise ValueError("Name must not be empty.")
        if len(name.strip()) == 0:
            raise ValueError("Name must contain non-whitespace characters.")

        # Ensure make argument satisfies type and value pre-conditions        
        if not isinstance(make, str):
            raise TypeError("Make must be a str.")
        if len(make) == 0:
            raise ValueError("Make must not be empty.")
        if len(make.strip()) == 0:
            raise ValueError("Make must contain non-whitespace characters.")
        
        # Ensure maximum volume per well argument satisfies type requirement       
        if not isinstance(max_volume_per_well, str):
            raise TypeError("Maximum volume must be a str.")
        
        # Attempt to parse maximum volume argument into a value-unit pair  
        try:
            parsed_result = Unit.parse_quantity(max_volume_per_well)
        except ValueError as e:
            raise ValueError(f"Could not parse maximum volume per well "
                             f"'{max_volume_per_well}'. {e}")\
                  from None
        max_volume_per_well, max_volume_unit = parsed_result

        # Ensure the quantity represents a valid volume for a container
        if max_volume_unit != 'L':
            raise ValueError("Maximum volume per well must have volume units "
                             "(e.g. L, mL, uL, etc.).")
        if not max_volume_per_well > 0:
            raise ValueError("Maximum volume per well must be positive.")

        # Set plate name, make and maximum volume attributes based on arguments
        self.name = name
        self.make = make
        self.max_volume_per_well = Unit.convert_to_storage(max_volume_per_well, 
                                                           'L')

        # Ensure rows argument satisfies type and value pre-conditions
        row_type_error_msg = "Rows must be an integer or an iterable set " \
                             "of row names."
        if isinstance(rows, int) and not isinstance(rows, bool):
            if rows < 1:
                raise ValueError("Number of rows must be positive. " \
                                f"Rows: {rows}")
            self.n_rows = rows
            
            # Define row names as alphabetic strings based on row index. 
            # E.g. 1 -> A
            #      2 -> B
            #       ...
            #      26 -> Z
            #      27 -> AA
            #      28 -> AB
            #       ...
            self.row_names = []
            for row_num in range(1, rows + 1):
                result = []
                while row_num > 0:
                    row_num -= 1
                    result.append(chr(ord('A') + row_num % 26))
                    row_num //= 26
                self.row_names.append(''.join(reversed(result)))
        
        elif isinstance(rows, Iterable) and not isinstance(rows, str):
            if len(rows) == 0:
                raise ValueError("Number of rows must be positive. " \
                                f"Rows: {rows}")
            for row in rows:
                if not isinstance(row, str):
                    raise TypeError(f"{row_type_error_msg} " \
                                    f"Non-string element: {row}")
                if len(row) == 0:
                    raise ValueError("Row names must not be empty.")
                if len(row.strip()) == 0:
                    raise ValueError("Row names must contain non-whitespace " \
                                     "characters.")
                
            if len(rows) != len(set(rows)):
                raise ValueError("Row names must not be duplicated.")
            
            self.n_rows = len(rows)
            self.row_names = rows
        
        else:
            raise TypeError(row_type_error_msg)

        # Ensure columns argument satisfies type and value pre-conditions
        col_type_error_msg = "Columns must be an integer or an iterable set " \
                             "of column names."
        if isinstance(columns, int) and not isinstance(columns, bool):
            if columns < 1:
                raise ValueError("Number of columns must be positive. " \
                                f"Columns: {columns}")
            self.n_columns = columns
            
            # Define column names as one-index column indices.
            # E.g. 0 -> 1
            #      1 -> 2
            #      2 -> 3
            #      ...
            self.column_names = [f"{i + 1}" for i in range(columns)]
        
        elif isinstance(columns, Iterable) and not isinstance(columns, str):
            if len(columns) == 0:
                raise ValueError("Number of columns must be positive. " \
                                f"Columns: {columns}")
            
            for column in columns:
                if not isinstance(column, str):
                    raise TypeError(f"{col_type_error_msg} " \
                                    f"Non-string element: {column}")
                if len(column) == 0:
                    raise ValueError("Column names must not be empty.")
                if len(column.strip()) == 0:
                    raise ValueError("Column names must contain non-" \
                                     "whitespace characters.")
                
            if len(columns) != len(set(columns)):
                raise ValueError("Column names must not be duplicated.")
            
            self.n_columns = len(columns)
            self.column_names = columns
        
        else:
            raise TypeError(col_type_error_msg)
        
        self.wells = np.array([
            [
                Container(f"Well {row}_{col}", 
                          max_volume=f"{max_volume_per_well} L")
                for col in self.column_names
            ]
            for row in self.row_names
        ])

    def __getitem__(self, item) -> PlateSlicer:
        return PlateSlicer(self, item)

    def __eq__(self, other):
        if not isinstance(other, Plate):
            return False
        return (self.name == other.name and
                self.make == other.make and
                self.max_volume_per_well == other.max_volume_per_well and
                self.n_rows == other.n_rows and
                self.n_columns == other.n_columns and
                self.row_names == other.row_names and
                self.column_names == other.column_names and
                np.array_equal(self.wells, other.wells))

    def __repr__(self):
        return f"Plate: {self.name}"

    def get_volumes(self, 
                    unit:str = None,
                    substance:(Substance|Iterable[Substance]) = None,
                    ) -> np.ndarray:
        """

        Arguments:
            unit: unit to return volumes in.
            substance: (optional) Substance to display volumes of.

        Returns:
            numpy.ndarray of volumes for each well in desired unit.

        """

        # Arguments are type checked in PlateSlicer.volumes
        return self[:].get_volumes(unit=unit, substance=substance)

    def get_volume(self, 
                   unit:str = None,
                   substance:(Substance|Iterable[Substance]) = None,
                   ) -> float:
        """
        Arguments:
            unit: unit to return volumes in.

        Returns: total volume stored in slice in uL.
        """
        return self.get_volumes(unit=unit, substance=substance).sum()

    def get_substances(self) -> set[Substance]:
        """

        Returns: A set of substances present in the slice.

        """
        return self[:].get_substances()

    def get_moles(self, 
                  substance:(Substance|Iterable[Substance]), 
                  unit:str = None) -> np.ndarray:
        """

        Arguments:
            unit: unit to return moles in. ('mol', 'mmol', 'umol', etc.)
            substance: Substance to display moles of.

        Returns: moles of substance in each well.
        """

        # Arguments are type checked in PlateSlicer.moles
        return self[:].get_moles(substance=substance, unit=unit)

    def dataframe(self, 
                  unit:str = None, 
                  substance:(str|Substance|Iterable[Substance]) = 'all',
                  cmap:str = None, 
                  highlight=False) -> Styler:
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
        return self[:].dataframe(substance=substance, 
                                 unit=unit, 
                                 cmap=cmap, 
                                 highlight=highlight)

    @staticmethod
    def transfer(source: Container | Plate | PlateSlicer, 
                 destination: Plate | PlateSlicer, 
                 quantity: str) \
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
        if not isinstance(source, (Container, Plate, PlateSlicer)):
            raise TypeError("Source must be a Container, Plate, or PlateSlicer.")
        if not isinstance(destination, (Plate, PlateSlicer)):
            raise TypeError("Destination must be a Plate or PlateSlicer.")
        if not isinstance(quantity, str):
            raise TypeError("Quantity must be a str.")
        
        if isinstance(source, Plate):
            source = source[:]
        if isinstance(destination, Plate):
            destination = destination[:]
        # noinspection PyProtectedMember
        return PlateSlicer._transfer(source, destination, quantity)

    def remove_substances(self, 
                          substances: Substance | Iterable[Substance]) -> Plate:
        """
        Removes substances from this plate.

        Arguments:
            remove_substances (Substance | Iterable[Substance]): 
                The specific Substance(s) to remove from the container.

        Returns: New Plate with requested substances removed.
        """
        if not isinstance(self, Plate):
            msg = "'Plate.remove_substances()' must be called on a Plate."
            raise TypeError(msg)

        return self[:].remove_substances(substances)
    
    # TODO: Replace the `int` type with a proper Substance type enum
    def remove_by_type(self, 
                       substance_types: int | Iterable[int]) -> Plate:
        """
        Removes substances from this plate by type (e.g. remove all liquids).

        Arguments:
            substance_types (int | Iterable[int]): 
                The Substance types to remove from the container. Must be a 
                supported Substance type (e.g. Substance.LIQUID).

        Returns: New Plate with requested substances removed.
        """
        if not isinstance(self, Plate):
            msg = "'Plate.remove_by_type()' must be called on a Plate."
            raise TypeError(msg)

        return self[:].remove_by_type(substance_types)

    def fill_to(self, 
                solvent:Substance, 
                quantity:str):
        """
        Fills all wells in plate with `solvent` up to `quantity`.

        Arguments:
            solvent (Substance): Substance to use to fill.
            quantity (str): Desired final quantity in each well.

        Returns: New Plate with desired final `quantity` in each well.

        """
        return self[:].fill_to(solvent, quantity)
    
class PlateSlicer(Slicer):
    """
    Represents a slice of a Plate.
    """

    plate: Plate

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
    def array(self, array: np.ndarray):
        self.plate.wells = array

    def get_dataframe(self):
        return pandas.DataFrame(self.plate.wells, 
                                columns=self.plate.column_names,
                                index=self.plate.row_names)

    @staticmethod
    def _transfer(frm:(Container | PlateSlicer), 
                  to:(PlateSlicer), 
                  quantity:str
            ) -> Tuple[Container | Plate, Plate]:
        
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
                assert isinstance(frm_array, np.ndarray)
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

            func = np.frompyfunc(helper, 2, 2)
            frm_result, to_result = func(frm.get(), to.get())
            frm.set(frm_result)
            to.set(to_result)
        else:
            raise ValueError("Source and destination slices must be the same size and shape.")

        return frm.plate, to.plate

    def highlight_wells(self, styler:Styler) -> Styler:
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

    def dataframe(self, 
                  unit:str = None, 
                  substance:(str|Substance|Iterable[Substance]) = 'all',
                  cmap:str = None, 
                  highlight:bool = False) -> Styler:
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

        def helper(elem : Container):
            if '/' in unit or unit[-1] == 'm' or unit[-1] == 'M':
                """ Returns concentration of substance in elem. """
                return elem.get_concentration(substance, unit)
            # else
            """ Returns amount of substance in elem. """
            if substance == 'all':
                amount = 0
                for subst, quantity in elem.contents.items():
                    amount += subst.convert(quantity, config.moles_storage_unit, unit)
                return amount
            elif isinstance(substance, Iterable):
                amount = 0
                for subst in substance:
                    amount += subst.convert(elem.contents.get(subst, 0), config.moles_storage_unit, unit)
                return amount
            else:
                return substance.convert(elem.contents.get(substance, 0), config.moles_storage_unit, unit)

        precision = config.precisions[unit] if unit in config.precisions else config.precisions['default']
        df = self.get_dataframe().apply(np.vectorize(helper, cache=True, otypes='d'))
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

    def get_volumes(self, 
                    unit:str = None,
                    substance:(Substance|Iterable[Substance]) = None, 
                    ) -> np.ndarray:
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
            return np.vectorize(lambda elem: elem.get_volume(unit),
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
                for subs, value in elem.contents.items():
                    amount += subs.convert(value, config.moles_storage_unit, unit)
            else:
                for subs in substance:
                    amount += subs.convert(elem.contents.get(subs, 0), config.moles_storage_unit, unit)
            return amount

        return np.vectorize(helper, cache=True, otypes='d')(self.get()).round(precision)

    def get_substances(self) -> set[Substance]:
        """

        Returns: A set of substances present in the plate.

        """
        substances_arr = np.vectorize(lambda elem: set(elem.contents.keys()), cache=True)(self.get())
        return set.union(*substances_arr.flatten())

    def get_moles(self, 
                  substance:(Substance|Iterable[Substance]), 
                  unit:str='mol') -> np.ndarray:
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
                amount += subs.convert(elem.contents.get(subs, 0), config.moles_storage_unit, unit)
            return amount

        return np.vectorize(helper, cache=True, otypes='d')(self.get()).round(precision)

    def remove_substances(self, 
                            substances: Substance | Iterable[Substance]) -> Plate:
        """
        Removes specified substances from all wells in the slice.

        Arguments:
            substances (Substance | Iterable[Substance]): 
                The specific Substance(s) to remove from the containers in the 
                slice.

        Returns: New Plate with requested substances removed from the slice.
        """
            
        self.plate = deepcopy(self.plate)
        self.apply(lambda elem: elem.remove_substances(substances))
        return self.plate

    # TODO: Replace `int` with a proper Substance type enum
    def remove_by_type(self, 
                        substance_types: int | Iterable[int]) -> Plate:
        """
        Removes substances of specified types from all wells in the slice.

        Arguments:
            substance_types (int | Iterable[int]): 
                The Substance type(s) to remove from the containers in the 
                slice. Must be supported Substance types (e.g., 
                Substance.LIQUID).

        Returns: New Plate with requested substance types removed from the 
            slice.
        """
       
        self.plate = deepcopy(self.plate)
        self.apply(lambda elem: elem.remove_by_type(substance_types))
        return self.plate

    def fill_to(self, 
                solvent:Substance, 
                quantity:str) -> Plate:
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