import numpy as np
import pdb
from pyplate import Recipe, Container
import pytest
import logging


def test_substance_used(water):
    container = Container('container', initial_contents=((water, '100 mL'),))
    #salt_water = Container.create_solution(salt, water, concentration='1 M', total_quantity='100 mL')
    container2 = Container('container2')
    recipe = Recipe()
    recipe.uses(container, container2)
    recipe.transfer(source=container, destination=container2, quantity='10 mL')
    recipe.bake()
    assert recipe.get_substance_used(substance=water, timeframe='all', unit='mL', destinations=[container2]) == 10.0

