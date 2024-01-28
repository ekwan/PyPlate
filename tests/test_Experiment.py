import pytest
from pyplate.experiment_design import Factor, Experiment, ExperimentalSpace
from pyplate.pyplate import Container


@pytest.fixture
def example_experiment():
    factors = {"Factor1": "Value1", "Factor2": "Value2"}
    return Experiment(factors, 1, 0)


# Tests for the Experiment class
def test_experiment_creation(example_experiment):
    assert example_experiment.experiment_id == 1
    assert example_experiment.replicate_idx == 0
    assert example_experiment.well is None


def test_experiment_mapping_well(example_experiment):
    well = Container("96-well")
    example_experiment.map_well(well)
    assert example_experiment.well == well


def test_experiment_repr(example_experiment):
    expected_repr = "Experiment({'Factor1': 'Value1', 'Factor2': 'Value2'}, 1, 0, None)"
    assert repr(example_experiment) == expected_repr


def test_experiment_str(example_experiment):
    expected_str = "Experiment: {'Factor1': 'Value1', 'Factor2': 'Value2'} with experiment_id 1 and replicate_idx 0"
    assert str(example_experiment) == expected_str


def test_experiment_getitem(example_experiment):
    assert example_experiment["Factor1"] == "Value1"


def test_experiment_setitem(example_experiment):
    example_experiment["Factor1"] = "ModifiedValue"
    assert example_experiment["Factor1"] == "ModifiedValue"


def test_experiment_contains(example_experiment):
    assert "Factor1" in example_experiment
    assert "NonexistentFactor" not in example_experiment


def test_experiment_iter(example_experiment):
    factors_iterator = iter(example_experiment)

    # Check that the iterator returns the factors in the expected order
    assert next(factors_iterator) == "Factor1"
    assert next(factors_iterator) == "Factor2"

    # Check that trying to get the next element raises StopIteration
    with pytest.raises(StopIteration):
        next(factors_iterator)


def test_experiment_len(example_experiment):
    assert len(example_experiment) == 2
