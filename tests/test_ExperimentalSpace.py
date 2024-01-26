import pytest
from pyplate.experiment_design import Factor, Experiment, ExperimentalSpace
import re
import collections


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


@pytest.fixture
def cookie_experimental_space():
    f1 = Factor(name="Baking Time", possible_values=[10, 20, 30], verifier=lambda: True)
    f2 = Factor(name="Baking Temperature", possible_values=[300, 350, 400], verifier=lambda: True)
    f3 = Factor(name="Flavor", possible_values=["Chocolate Chip", "Oatmeal Raisin", "Peanut Butter"],
                verifier=lambda: True)

    return ExperimentalSpace(factors={f1, f2, f3}, experiment_id_generator=lambda: 1)


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


def test_experimental_space_generate_experiments(cookie_experimental_space):
    expected_exps = \
        [
            # 300 temp, chocolate chip block
            [
                Experiment({'Baking Temperature': 300, 'Flavor': 'Chocolate Chip', 'Baking Time': 10}, 1, 1, None),
                Experiment({'Baking Temperature': 300, 'Flavor': 'Chocolate Chip', 'Baking Time': 10}, 1, 2, None),
                Experiment({'Baking Temperature': 300, 'Flavor': 'Chocolate Chip', 'Baking Time': 30}, 1, 1, None),
                Experiment({'Baking Temperature': 300, 'Flavor': 'Chocolate Chip', 'Baking Time': 30}, 1, 2, None)
            ],

            # 300 temp, oatmeal raisin block
            [
                Experiment({'Baking Temperature': 300, 'Flavor': 'Oatmeal Raisin', 'Baking Time': 10}, 1, 1, None),
                Experiment({'Baking Temperature': 300, 'Flavor': 'Oatmeal Raisin', 'Baking Time': 10}, 1, 2, None),
                Experiment({'Baking Temperature': 300, 'Flavor': 'Oatmeal Raisin', 'Baking Time': 30}, 1, 1, None),
                Experiment({'Baking Temperature': 300, 'Flavor': 'Oatmeal Raisin', 'Baking Time': 30}, 1, 2, None)
            ],

            # 300 temp, peanut butter block
            [
                Experiment({'Baking Temperature': 300, 'Flavor': 'Peanut Butter', 'Baking Time': 10}, 1, 1, None),
                Experiment({'Baking Temperature': 300, 'Flavor': 'Peanut Butter', 'Baking Time': 10}, 1, 2, None),
                Experiment({'Baking Temperature': 300, 'Flavor': 'Peanut Butter', 'Baking Time': 30}, 1, 1, None),
                Experiment({'Baking Temperature': 300, 'Flavor': 'Peanut Butter', 'Baking Time': 30}, 1, 2, None)
            ],

            # 350 temp, chocolate chip block
            [
                Experiment({'Baking Temperature': 350, 'Flavor': 'Chocolate Chip', 'Baking Time': 10}, 1, 1, None),
                Experiment({'Baking Temperature': 350, 'Flavor': 'Chocolate Chip', 'Baking Time': 10}, 1, 2, None),
                Experiment({'Baking Temperature': 350, 'Flavor': 'Chocolate Chip', 'Baking Time': 30}, 1, 1, None),
                Experiment({'Baking Temperature': 350, 'Flavor': 'Chocolate Chip', 'Baking Time': 30}, 1, 2, None)
            ],

            # 350 temp, oatmeal raisin block
            [
                Experiment({'Baking Temperature': 350, 'Flavor': 'Oatmeal Raisin', 'Baking Time': 10}, 1, 1, None),
                Experiment({'Baking Temperature': 350, 'Flavor': 'Oatmeal Raisin', 'Baking Time': 10}, 1, 2, None),
                Experiment({'Baking Temperature': 350, 'Flavor': 'Oatmeal Raisin', 'Baking Time': 30}, 1, 1, None),
                Experiment({'Baking Temperature': 350, 'Flavor': 'Oatmeal Raisin', 'Baking Time': 30}, 1, 2, None)
            ],

            # 350 temp, peanut butter block
            [
                Experiment({'Baking Temperature': 350, 'Flavor': 'Peanut Butter', 'Baking Time': 10}, 1, 1, None),
                Experiment({'Baking Temperature': 350, 'Flavor': 'Peanut Butter', 'Baking Time': 10}, 1, 2, None),
                Experiment({'Baking Temperature': 350, 'Flavor': 'Peanut Butter', 'Baking Time': 30}, 1, 1, None),
                Experiment({'Baking Temperature': 350, 'Flavor': 'Peanut Butter', 'Baking Time': 30}, 1, 2, None)
            ]
        ]
    generated_exps = cookie_experimental_space.generate_experiments(
        factors={
            "Baking Time": [10, 30],
            "Baking Temperature": [300, 350],
            "Flavor": "all"
        },
        n_replicates=2,
        blocking_factors=["Baking Temperature", "Flavor"]
    )

    for block in generated_exps:
        assert collections.Counter(block) == collections.Counter(expected_exps.pop(0))
