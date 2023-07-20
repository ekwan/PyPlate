from functools import cached_property
# from typing import Union, Tuple, List
import numpy as np


# Valid slices:
#
# Label = Union(str, int)
#
# Slice                                             ->      item
#       shape                                               size
#
# array['A:1'] or array['A', '1'] or array[1, 1]    ->      str or Tuple[Label, Label]
#       ()                                                  1
#
# array[i:j]                                        ->      Slice
#       (n, n_cols)                                         n * n_cols
#
# array[i:j, 1]                                     ->      Tuple[Slice, Label]
#       (n,)                                                n
#
# array[1, i:j]                                     ->      Tuple[Label, Slice]
#       (n,)                                                n
#
# array[i:j, k:l]                                   ->      Tuple[Slice, Slice]
#       (n, o)                                              n * o
#
# array[['A:1', ('A', '1'), (1,1)]]                 ->      List[Union[Label, Tuple[Label, Label]]
#       (3,)                                                3

class Slicer:
    # Label = Union[str, int]
    # Single = Union[str, Tuple[Label, Label]]
    # Singles = Union[List[Single], Single]
    # Plate_Slice = Union[Singles, Tuple[slice, Label], Tuple[Label, slice], Tuple[slice, slice]]

    @staticmethod
    def _is_label(item):
        return isinstance(item, int) or isinstance(item, int)

    @classmethod
    def _is_single(cls, item):
        return isinstance(item, str) or \
            (isinstance(item, tuple) and len(item) == 2 and all(map(cls._is_label, item)))

    @classmethod
    def _is_singles(cls, item):
        return cls._is_single(item) or (isinstance(item, list) and all(map(cls._is_single, item)))

    def __init__(self, data, array_obj: np.ndarray, row_labels, col_labels, item):
        self.data = data
        self.array = array_obj
        self.col_labels = col_labels
        self.n_cols = len(col_labels)
        self.row_labels = row_labels
        self.n_rows = len(row_labels)
        self.item = item

        assert array_obj.shape == (self.n_rows, self.n_cols)

        if isinstance(item, str):
            self.slices = self.parse_single(item)
        elif isinstance(item, list):
            self.slices = list(map(self.parse_single, item))
        elif isinstance(item, int):
            assert item >= 1
            self.slices = item - 1
        else:
            self.slices = self.parse_item(item)

    def parse_single(self, single):  # 'A:1' or ('A','1') or (1, 1)
        if isinstance(single, str) and ':' in single:
            single = tuple(single.split(':'))
        if isinstance(single, tuple) and len(single) == 2:
            return (self.resolve_labels(single[0], self.row_labels),
                    self.resolve_labels(single[1], self.col_labels))
        raise ValueError("Invalid slice.")

    def parse_item(self, item):
        if isinstance(item, tuple) and len(item) == 1:
            item = item[0]
        if isinstance(item, tuple) and len(item) == 2:
            return (self.resolve_labels(item[0], self.row_labels),
                    self.resolve_labels(item[1], self.col_labels))
        elif isinstance(item, tuple):
            raise ValueError("We only have two axes.")
        else:
            return self.resolve_labels(item, self.row_labels)

    @staticmethod
    def resolve_labels(item, labels):
        if isinstance(item, int):
            assert item >= 1
            return item - 1  # Use one-based indexing
        if isinstance(item, str):
            try:
                return labels.index(item)
            except ValueError:
                raise ValueError(f"Label not found: {item}")
        if isinstance(item, slice):
            start, stop, step = item.start, item.stop, item.step
            assert step is None or isinstance(step, int)
            if isinstance(start, str):
                start = labels.index(start)
            elif isinstance(start, int):
                assert start >= 1
                start -= 1  # Use one-based indexing
            elif start is not None:
                raise ValueError("Start value must be a label or int.")

            if isinstance(stop, str):
                stop = labels.index(stop)
            elif isinstance(stop, int):
                assert stop >= 1
                stop -= 1  # Use one-based indexing
            elif stop is not None:
                raise ValueError("Stop value must be a label or int.")

            if stop is not None:
                stop += 1  # We want values up to and including stop.
            return slice(start, stop, step)
        raise ValueError("Invalid type for a slice.")

    def get(self):
        if isinstance(self.slices, list):
            return np.array(list(map(self.array.__getitem__, self.slices)))
        return self.array.__getitem__(self.slices)

    def set(self, values):
        assert np.shape(values) == self.shape
        if isinstance(self.slices, list):
            for index, value in zip(self.slices, values):
                self.array.__setitem__(index, value)
        else:
            self.array.__setitem__(self.slices, values)

    @cached_property
    def shape(self):
        return np.shape(self.get())

    @cached_property
    def size(self):
        return np.size(self.get())

    def __repr__(self):
        return f"Slice: {self.data}[{self.slices}]"
