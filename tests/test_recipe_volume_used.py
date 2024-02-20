import numpy as np
from pyplate.pyplate import Recipe, Container
import pytest

def test_simple_volume_used(salt_water, water):
    container = Container('container', initial_contents=[(water, '20 mL')])
    recipe = Recipe()
    recipe.uses(salt_water, container)
    recipe.transfer(salt_water, container, '10 mL')
    #recipe.transfer
    recipe.bake()
    
    #Assertions
    assert recipe.volume_used(container, 'all', 'mL') == 100
