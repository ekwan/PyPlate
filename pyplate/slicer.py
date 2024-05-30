from copy import copy
from functools import cached_property
from typing import Union, Tuple, List

import numpy
import numpy as np

__docformat__ = "google"

Label = Union[str, int]
"""@private"""
Single = Union[Label, Tuple[Label, Label]]
"""@private"""
Singles = Union[List[Single], Single]
"""@private"""
Slice = Union[Singles, slice, Tuple[slice, Label], Tuple[Label, slice],
              Tuple[slice, slice], Tuple[List[Single], slice], Tuple[slice, List[Single]]]
"""@private"""


class Slicer:
    """
    This is a helper class designed to facilitate slicing operations on composed numpy ndarrays.
    To use this class for a specific application, it needs to be extended.
    The class supports one-based integer indexing, meaning array[1,1] refers to the upper left element.
    Negative indexing is not currently supported.
    The item to be sliced can be specified in several ways:
    - A string in the format 'A:1' (for a single element)
    - A tuple in the format (1, 1) (for a single element)
    - A list of strings in the format 'A:1', or tuples in the format (1,1) (for multiple elements)
    - A single label or integer (for a row)
    - A label or integer and a slice (for a row and multiple columns)
    - A slice and a label or integer (for multiple rows and a column)
    - A slice
    - Two slices (for a row and column)

    Examples of valid slicing operations include:
    - Single string: ['A:1'], ['1:1']
    - Single tuple: [(1, 1)], [('A', '1')]
    - List of strings or tuples: [['A:1', 'B:2', (1,1), (2,2), ('A','1'), ('B','2')]]
    - Single label or integer: [1], ['A']
    - Label or integer and a slice: [1, 1:], ['A', 1:], [1, '1':]
    - Slice and a label or integer: [1:, 1], ['A':, 1], [1:, '1'], ['A':, '1']
    - A slice: [1:], ['A':]
    - Two slices: [1:, 1:], ['A':, 1:], [1:, '1':], ['A':, '1':]

    The resulting slices will be either a single view or a list of views.
    """

    def __init__(self, array_obj: np.ndarray, row_labels: tuple | list, col_labels: tuple | list,
                 item: Slice | list):
        """

        Args:
            array_obj (numpy.ndarry): Array to slice.
            row_labels (list): Row labels.
            col_labels (list): Column labels.
            item: Slice(s) passed to __getitem__.
        """

        if not isinstance(array_obj, np.ndarray):
            raise TypeError("array must be a numpy.ndarray.")
        self.array = array_obj
        if not isinstance(row_labels, list) or not all(isinstance(elem, str) for elem in row_labels):
            raise TypeError("row_labels myst be a list of strings.")
        if not isinstance(col_labels, list) or not all(isinstance(elem, str) for elem in col_labels):
            raise TypeError("col_labels myst be a list of strings.")
        self.row_labels = row_labels
        self.n_rows = len(row_labels)
        self.col_labels = col_labels
        self.n_cols = len(col_labels)
        self.item = item

        if array_obj.shape != (self.n_rows, self.n_cols):
            raise ValueError("Length of labels must match shape of array.")

        if isinstance(item, str):
            if ':' in item:
                row, col = self.parse_single(item)
                self.slices = (slice(row, row + 1), slice(col, col + 1))
            else:
                row = self.resolve_labels(item, self.row_labels)
                self.slices = (slice(row, row + 1), slice(None))
        elif isinstance(item, list):
            self.slices = []
            for elem in item:
                if isinstance(elem, tuple):
                    row, col = self.parse_tuple(elem)
                    self.slices.append((slice(row, row + 1), slice(col, col + 1)))
                elif isinstance(elem, str) and ':' in elem:
                    row, col = self.parse_single(elem)
                    self.slices.append((slice(row, row + 1), slice(col, col + 1)))
                else:
                    raise TypeError("Invalid slice.")
        elif isinstance(item, int):
            if not 1 <= item <= self.n_rows:
                raise ValueError("Row index out of range.")
            self.slices = (slice(item - 1, item), slice(None))
        elif isinstance(item, slice):
            self.slices = (self.parse_slice(item, self.row_labels), slice(None))
        elif isinstance(item, tuple):
            if len(item) == 1 and isinstance(item[0], slice):
                self.slices = (Slicer.parse_slice(item[0], self.row_labels), slice(None))
            if len(item) == 2:
                if isinstance(item[0], (int, str)) and isinstance(item[1], (int, str)):
                    row = self.resolve_labels(item[0], self.row_labels)
                    col = self.resolve_labels(item[1], self.col_labels)
                    self.slices = (slice(row, row + 1), slice(col, col + 1))
                elif isinstance(item[0], slice) and isinstance(item[1], slice):
                    self.slices = (Slicer.parse_slice(item[0], self.row_labels),
                                   Slicer.parse_slice(item[1], self.col_labels))
                elif isinstance(item[0], slice) and isinstance(item[1], (int, str)):
                    col = self.resolve_labels(item[1], self.col_labels)
                    if not 0 <= col < self.n_cols:
                        raise ValueError("Column index out of range.")
                    self.slices = (self.resolve_labels(item[0], self.row_labels), slice(col, col + 1))
                elif isinstance(item[0], (int, str)) and isinstance(item[1], slice):
                    row = self.resolve_labels(item[0], self.row_labels)
                    if not 0 <= row < self.n_rows:
                        raise ValueError("Row index out of range.")
                    self.slices = (slice(row, row + 1), self.resolve_labels(item[1], self.col_labels))
                else:
                    raise TypeError("Invalid slice.")
            else:
                raise TypeError("Invalid slice.")
        else:
            raise TypeError("Invalid slice.")

    def copy(self):
        return Slicer(self.array, self.row_labels, self.col_labels, self.item)

    def parse_single(self, single) -> Tuple[int, int]:
        """
        Convert a single index to a tuple of integers.

        Args:
            single: Index to parse, i.e. 'A:1' or ('A','1') or (1, 1).

        """
        if isinstance(single, str) and ':' in single:
            single = tuple(single.split(':'))
        if isinstance(single, tuple) and len(single) == 2:
            return (self.resolve_labels(single[0], self.row_labels),
                    self.resolve_labels(single[1], self.col_labels))
        raise TypeError("Invalid slice.")

    def parse_tuple(self, item):
        """
        Handle cases where item is a tuple.

        Args:
            item: Tuples from slice(s) passed to __getitem__.

        Returns:
            Resolved tuples(s).

        """
        if isinstance(item, tuple) and len(item) == 1:
            item = item[0]
        if isinstance(item, tuple) and len(item) == 2:
            if isinstance(item[0], (str, int)) and isinstance(item[1], (str, int)):
                return self.resolve_labels(item[0], self.row_labels), self.resolve_labels(item[1], self.col_labels)
            else:
                raise TypeError("Invalid slice.")
        elif isinstance(item, tuple):
            raise ValueError("We only have two axes.")
        else:
            raise TypeError("Invalid slice.")

    @staticmethod
    def parse_slice(item, labels: List[str]) -> slice:
        """
        Convert a slice to a tuple of integers.

        Args:
            labels: Row or column labels.
            item: Slice to parse, i.e. slice(1, None, None) or slice('A', None, None).

        """
        if isinstance(item, slice):
            start, stop, step = item.start, item.stop, item.step
            if not (step is None or isinstance(step, int)):
                raise TypeError("Step must be None or an integer")
            if start is not None:
                if isinstance(start, str):
                    start = Slicer.resolve_labels(start, labels)
                elif isinstance(start, int):
                    if not 1 <= start <= len(labels):
                        raise ValueError("Index out of range")
                    start -= 1
                else:
                    raise TypeError("Invalid type for start.")
            if stop is not None:
                if isinstance(stop, str):
                    if stop not in labels:
                        raise ValueError(f"Label not found: {stop}")
                    stop = labels.index(stop) + 1
                elif isinstance(stop, int):
                    if not 1 <= stop <= len(labels):
                        raise ValueError("Index out of range")
                    # stop is not decremented because slice() is exclusive
                else:
                    raise TypeError("Invalid type for stop.")
            return slice(start, stop, step)
        raise TypeError("Invalid slice.")

    @staticmethod
    def resolve_labels(item: str | slice, labels: List[str]) -> int | slice:
        """
        Convert argument passed into __getitem__ to only contain integer indices.

        Args:
            item: String or slice passed to __getitem__.
            labels: Row or column labels.

        Returns: Converted item.

        """
        if isinstance(item, int):
            if not 1 <= item <= len(labels):
                raise ValueError("Index out of range")
            return item - 1
        elif isinstance(item, str):
            if item in labels:
                return labels.index(item)
            else:
                raise ValueError(f"Label not found: {item}")
        elif isinstance(item, slice):
            return Slicer.parse_slice(item, labels)

    def get(self):
        """
        Get data pointed to by slices.
        """
        if isinstance(self.slices, list):
            return np.array(list(map(self.array.__getitem__, self.slices))).flatten()
        return self.array.__getitem__(self.slices)

    def apply(self, func):
        """
        Apply function to data pointed to by slices.

        Args:
            func: Function to apply.

        Returns:
            Result of function.

        """
        if isinstance(self.slices, list):
            for elem in self.slices:
                result = numpy.vectorize(func, cache=True)(self.array.__getitem__(elem))
                self.array.__setitem__(elem, result)
        else:
            self.array.__setitem__(self.slices, numpy.vectorize(func, cache=True)(self.array.__getitem__(self.slices)))

    def set(self, values):
        """
        Replace data pointed to by slice(s).

        Shape and size of values must match the shape and size of stored slice(s).

        Args:
            values: Data to store.

        Raises:
            ValueError: Shape or size doesn't match.
        """
        if isinstance(values, list):
            if len(values) != len(self.slices):
                raise ValueError("Shape or size of values doesn't match.")
            for index, value in zip(self.slices, values):
                self.array.__setitem__(index, [[value]])
        elif isinstance(values, np.ndarray):
            if np.shape(values) != self.shape or np.size(values) != self.size:
                raise ValueError("Shape or size of values doesn't match.")
            self.array.__setitem__(self.slices, values)
        else:
            self.array.__setitem__(self.slices, [[values]])

    @cached_property
    def shape(self):
        """
        Gets shape of selected slice(s).
        """
        return np.shape(self.get())

    @cached_property
    def size(self):
        """
        Gets size of selected slice(s).
        """
        return np.size(self.get())

    def __repr__(self):
        return f"Slice: [{self.slices}]"

    @staticmethod
    def _process_sub_slice(curr_slice: slice, sub_slice: slice, labels):
        start, stop, step = curr_slice.start, curr_slice.stop, curr_slice.step
        if start is None:
            start = 0
        if stop is None:
            stop = len(labels)
        if step is None:
            step = 1
        if sub_slice.start is None:
            sub_slice = slice(0, sub_slice.stop, sub_slice.step)

        if sub_slice.start is not None and sub_slice.start < 0:
            sub_slice = slice(stop + sub_slice.start, sub_slice.stop, sub_slice.step)
        if sub_slice.stop is not None and sub_slice.stop < 0:
            sub_slice = slice(sub_slice.start, stop + sub_slice.stop, sub_slice.step)
        if sub_slice.stop is None:
            length = float('inf')
        else:
            length = sub_slice.stop - sub_slice.start

        start = start + sub_slice.start * step
        stop = min(start + length * step, stop)
        if sub_slice.step is not None:
            step *= sub_slice.step

        if start == 0:
            start = None
        if stop >= len(labels):
            stop = None
        if step == 1:
            step = None
        return slice(start, stop, step)

    def __getitem__(self, item):
        # negative indexing not supported
        if isinstance(self.slices, list):
            new_slicer = copy(self)
            new_slicer.slices = new_slicer.slices.__getitem__(item)
            return new_slicer

        if isinstance(item, (int, slice)):
            item = (item, slice(None))
        if isinstance(item, tuple) and len(item) == 2:
            if isinstance(item[0], int):
                row = item[0]
                item = (slice(row, row + 1), item[1])
            if isinstance(item[1], int):
                col = item[1]
                item = (item[0], slice(col, col + 1))
            if isinstance(item[0], slice) and isinstance(item[1], slice):
                new_slicer = copy(self)
                new_slicer.items = item
                new_slicer.slices = (Slicer._process_sub_slice(self.slices[0], item[0], self.row_labels),
                                     Slicer._process_sub_slice(self.slices[1], item[1], self.col_labels))
                return new_slicer
            else:
                raise TypeError("Invalid slice.")
        else:
            raise TypeError("Invalid slice.")
