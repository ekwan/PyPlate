import pytest
from pyplate import Substance, Container, Plate


@pytest.fixture
def salt() -> Substance:
    return Substance.solid('NaCl', 58.4428, 2.17)


@pytest.fixture
def water() -> Substance:
    return Substance.liquid('H2O', mol_weight=18.0153, density=1)


@pytest.fixture
def empty_container() -> Container:
    return Container('empty')


@pytest.fixture
def water_stock(water) -> Container:
    return Container('water', initial_contents=((water, '10 mL'),))


@pytest.fixture
def salt_water(water, salt) -> Container:
    return Container('salt water', initial_contents=((water, '100 mL'), (salt, '50 mmol')))


@pytest.fixture
def dmso() -> Substance:
    return Substance.liquid('DMSO', 78.13, 1.1004)


@pytest.fixture
def sodium_sulfate() -> Substance:
    return Substance.solid('Sodium sulfate', 142.04, 2.66)


@pytest.fixture
def triethylamine() -> Substance:
    return Substance.liquid("triethylamine", mol_weight=101.19, density=0.726)

@pytest.fixture
def invalid_substance() -> Substance:
    substance = Substance.solid('invalid', 1, 1)
    substance.mol_weight = 0
    substance.density = 0
    substance._type = 0
    return substance

@pytest.fixture
def empty_plate() -> Plate:
    return Plate('plate', '200 uL')


@pytest.fixture
def water_plate(water, empty_plate) -> Plate:
    return empty_plate.fill_to(water, '100 uL')
