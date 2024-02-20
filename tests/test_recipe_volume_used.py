import numpy as np

from pyplate.pyplate import Recipe, Container
import pytest


def test_volume_used_fill_to(salt, water):
    water_container = Container('container')
    recipe = Recipe().uses(water_container)
    recipe.fill_to(water_container, water, '10 mL')
    recipe.bake()

    assert recipe.volume_used(container=water_container, timeframe='all', unit='mL') == {"in": 10.0, "out": 0.0}
