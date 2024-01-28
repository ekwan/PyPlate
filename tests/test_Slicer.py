import pytest
import numpy as np
from pyplate.slicer import Slicer


@pytest.fixture
def array():
    return np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])


@pytest.fixture
def row_labels():
    return ['A', 'B', 'C']


@pytest.fixture
def col_labels():
    return ['1', '2', '3', '4']


def test_resolve_labels_zero():
    # Index must be in range 1..n
    with pytest.raises(ValueError):
        Slicer.resolve_labels(0, [])


def test_resolve_labels_high():
    # Index must be in range 1..n
    with pytest.raises(ValueError):
        Slicer.resolve_labels(100, ['1'])


def test_resolve_labels_high_slices():
    # Slice indexes must be in range 1..n
    with pytest.raises(ValueError):
        Slicer.resolve_labels(slice(100, None, None), ['1'])
    with pytest.raises(ValueError):
        Slicer.resolve_labels(slice(None, 100, None), ['1'])


def test_resolve_labels_not_in_labels():
    # Label must in list of labels
    with pytest.raises(ValueError):
        Slicer.resolve_labels('label', [])


def test_resolve_labels_invalid_step():
    # step must be None or int
    with pytest.raises(TypeError):
        Slicer.resolve_labels(slice(None, None, 'label'), [])


def test_Slicer_arraytype():
    # array_obj must be a numpy.ndarray
    with pytest.raises(TypeError, match="must be a numpy.ndarray"):
        Slicer(None, None, None, None)


def test_Slicer_row_labels(array):
    # row_labels must be a list or tuple
    with pytest.raises(TypeError, match="row_labels"):
        Slicer(array, None, None, None)
    # row_labels must not be empty
    with pytest.raises(TypeError, match="row_labels"):
        Slicer(array, (), None, None)


def test_Slicer_col_labels(array):
    # col_labels must be a list or tuple
    with pytest.raises(TypeError, match="col_labels"):
        Slicer(array, [], None, None)
    # col_labels must not be empty
    with pytest.raises(TypeError, match="col_labels"):
        Slicer(array, ['1'], (), None)


def test_single_string(array, row_labels, col_labels):
    # Test a single string
    s = Slicer(array, row_labels, col_labels, 'A:1')
    assert s.array is array
    assert s.row_labels is row_labels
    assert s.col_labels is col_labels
    assert s.slices == (slice(0, 1), slice(0, 1))
    assert np.array_equal(s.get(), np.array([[array[0, 0]]]))


def test_single_tuple(array, row_labels, col_labels):
    # Test a single tuple
    s = Slicer(array, row_labels, col_labels, ('A', '1'))
    assert s.array is array
    assert s.row_labels is row_labels
    assert s.col_labels is col_labels
    assert s.slices == (slice(0, 1), slice(0, 1))
    assert np.array_equal(s.get(), np.array([[array[0, 0]]]))


def test_list_of_strings(array, row_labels, col_labels):
    # Test a list of strings
    s = Slicer(array, row_labels, col_labels, ['A:1', 'B:2'])
    assert s.array is array
    assert s.row_labels is row_labels
    assert s.col_labels is col_labels
    assert s.slices == [(slice(0, 1), slice(0, 1)), (slice(1, 2), slice(1, 2))]
    assert np.array_equal(s.get(), np.array([array[0, 0], array[1, 1]]))


def test_single_label(array, row_labels, col_labels):
    # Test a single label
    s = Slicer(array, row_labels, col_labels, 'A')
    assert s.array is array
    assert s.row_labels is row_labels
    assert s.col_labels is col_labels
    assert s.slices == (slice(0, 1), slice(None))
    assert np.array_equal(s.get(), array[:1])


def test_single_int(array, row_labels, col_labels):
    # Test a single integer
    s = Slicer(array, row_labels, col_labels, 1)
    assert s.array is array
    assert s.row_labels is row_labels
    assert s.col_labels is col_labels
    assert s.slices == (slice(0, 1), slice(None))
    assert np.array_equal(s.get(), array[:1])


def test_single_label_and_slice(array, row_labels, col_labels):
    # Test a single label and a slice
    s = Slicer(array, row_labels, col_labels, ('A', slice(None)))
    assert s.array is array
    assert s.row_labels is row_labels
    assert s.col_labels is col_labels
    assert s.slices == (slice(0, 1), slice(None))
    assert np.array_equal(s.get(), array[:1, :])


def test_single_int_and_slice(array, row_labels, col_labels):
    # Test a single label and a slice
    s = Slicer(array, row_labels, col_labels, (1, slice(None)))
    assert s.array is array
    assert s.row_labels is row_labels
    assert s.col_labels is col_labels
    assert s.slices == (slice(0, 1), slice(None))
    assert np.array_equal(s.get(), array[:1, :])


def test_slice_and_single_label(array, row_labels, col_labels):
    # Test a single label and a slice
    s = Slicer(array, row_labels, col_labels, (slice(None), '1'))
    assert s.array is array
    assert s.row_labels is row_labels
    assert s.col_labels is col_labels
    assert s.slices == (slice(None), slice(0, 1))
    assert np.array_equal(s.get(), array[:, :1])


def test_slice_and_single_int(array, row_labels, col_labels):
    # Test a single label and a slice
    s = Slicer(array, row_labels, col_labels, (slice(None), 1))
    assert s.array is array
    assert s.row_labels is row_labels
    assert s.col_labels is col_labels
    assert s.slices == (slice(None), slice(0, 1))
    assert np.array_equal(s.get(), array[:, :1])


def test_test_two_slices(array, row_labels, col_labels):
    # Test two slices
    s = Slicer(array, row_labels, col_labels, (slice(None), slice(None)))
    assert s.array is array
    assert s.row_labels is row_labels
    assert s.col_labels is col_labels
    assert s.slices == np.s_[:, :]
    assert np.array_equal(s.get(), array[:, :])


def test_stop_label(array, row_labels, col_labels):
    # Test a stop label
    s = Slicer(array, row_labels, col_labels, (slice(None, 'B'), slice(None)))
    assert s.array is array
    assert s.row_labels is row_labels
    assert s.col_labels is col_labels
    assert s.slices == (slice(None, 2), slice(None))
    assert np.array_equal(s.get(), array[:2, ])


def test_stop_int(array, row_labels, col_labels):
    # Test a stop label
    s = Slicer(array, row_labels, col_labels, (slice(None, 2), slice(None)))
    assert s.array is array
    assert s.row_labels is row_labels
    assert s.col_labels is col_labels
    assert s.slices == (slice(None, 2), slice(None))
    assert np.array_equal(s.get(), array[:2, ])
