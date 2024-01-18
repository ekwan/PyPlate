import pytest
from pyplate.experiment_design import Factor, Experiment, ExperimentalSpace
import re


@pytest.fixture
def example_factor():
    return Factor("ExampleFactor", ["Value1", "Value2"], lambda x, y: True)


@pytest.fixture
def another_factor():
    return Factor("AnotherFactor", ["ValueA", "ValueB"], lambda x, y: True)


@pytest.fixture
def example_experiment(example_factor):
    factors = {"ExampleFactor": "Value1"}
    return Experiment(factors, 1, 0)


@pytest.fixture
def example_experimental_space(example_factor):
    return ExperimentalSpace(set(), lambda: 1)


# Tests for the ExperimentalSpace class
def test_experimental_space_register_factor_verification(example_experimental_space, example_factor):
    example_experimental_space.register_factor(example_factor)

    # Verify that registering a factor with the same name raises ValueError
    with pytest.raises(Exception, match=f"Factor {example_factor.name} already exists in experimental space"):
        example_experimental_space.register_factor(example_factor)


def test_experimental_space_add_experiment_verification(example_experimental_space, example_experiment, another_factor):
    example_experimental_space.register_factor(another_factor)

    # Verify that adding an experiment with factors not matching experimental space factors raises ValueError
    invalid_experiment = Experiment({"InvalidFactor": "Value1"}, 2, 0)
    with pytest.raises(ValueError, match=re.escape(f"Experiment factors {invalid_experiment.factors.keys()} "
                                                   f"do not match experimental space factors {example_experimental_space.factors}")):
        example_experimental_space.add_experiment(invalid_experiment)

    # Verify that adding an experiment with a factor value not in possible values raises ValueError
    invalid_experiment = Experiment({"AnotherFactor": "InvalidValue"}, 3, 0)
    with pytest.raises(ValueError, match=re.escape("Experiment factor AnotherFactor value InvalidValue "
                                                   f"not in possible values ['ValueA', 'ValueB']")):
        example_experimental_space.add_experiment(invalid_experiment)
