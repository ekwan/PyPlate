import pytest
from pyplate.experiment_design import Factor


@pytest.fixture
def example_factor():
    return Factor("ExampleFactor", ["Value1", "Value2"])


def test_factor_creation(example_factor):
    assert example_factor.name == "ExampleFactor"
    assert example_factor.possible_values == ["Value1", "Value2"]


def test_factor_representation(example_factor):
    assert (
        str(example_factor)
        == "Factor: ExampleFactor with possible values ['Value1', 'Value2']"
    )


def test_factor_equality(example_factor):
    # Create a copy of the example_factor
    copied_factor = Factor("ExampleFactor", ["Value1", "Value2"])

    # Check that the __eq__ method correctly identifies the factors as equal
    assert example_factor == copied_factor

    # Change a property and check that the factors are not equal
    copied_factor.possible_values = ["Value1", "Value2", "Value3"]
    assert example_factor != copied_factor
