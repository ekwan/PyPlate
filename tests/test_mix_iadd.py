import pytest
from PyPlate import Substance, Mixture


def test_mix_iadd_solid():
    salt = Substance.solid('NaCl', 58.4428)
    mix = Mixture('salt water')
    mix += (salt, '10 g')
    assert salt.id in mix.contents


def test_mix_iadd_liquid():
    water = Substance.liquid('H2O', 18.0153, 1)
    mix = Mixture('salt water')
    mix += (water, '10 mL')
    assert water.id in mix.contents
    assert mix.volume == 10


def test_mix_iadd_liquid_and_solid():
    water = Substance.liquid('H2O', 18.0153, 1)
    salt = Substance.solid('NaCl', 58.4428)
    mix = Mixture('salt water')
    mix += (water, '10 mL')
    mix += (salt, '10 g')
    assert water.id in mix.contents
    assert salt.id in mix.contents
    assert abs(mix.contents[water.id][1] - 0.55) <= 0.01
    assert abs(mix.contents[salt.id][1] - 0.1711) <= 0.0001
    assert mix.volume == 10
