import numpy as np
import pytest
from pyplate import Recipe, Container, Substance, Plate

def test_amount_remaining_simple(water, salt):
    recipe = Recipe()
    source = Container('source', initial_contents=((water, '100 mL'),))
    dest = Container('dest')
    recipe.uses(source, dest)
    recipe.transfer(source, dest, quantity='50 mL')
    recipe.bake()
    assert recipe.get_amount_remaining(dest, 'all', 'mL') == 50

def test_amount_remaining_plate(water, salt):
    recipe = Recipe()
    water_stock = Container('water stock', initial_contents=((water, '100 mL'),))
    source = Plate('source', '2 mL', rows=2, columns=2,)
    dest = Plate('dest', '1 mL', rows=2, columns=2)
    recipe.uses(source, dest, water_stock)
    recipe.transfer(water_stock, source, quantity='2 mL')
    recipe.transfer(source, dest, quantity='1 mL')
    recipe.bake()

    expected = np.ones((2, 2))
    assert pytest.approx(expected) == recipe.get_amount_remaining(source, 'all', 'mL')

def test_amount_remaining_stages_with_remove(water, salt):
    recipe = Recipe()
    source = Container('source', initial_contents=((water, '100 mL'),))
    dest = Container('dest')
    recipe.uses(source, dest)
    recipe.start_stage('stage 1')
    recipe.transfer(source, dest, quantity='50 mL')
    recipe.end_stage('stage 1')
    recipe.remove(dest, water)
    recipe.bake()
    assert recipe.get_amount_remaining(dest, 'all', 'mL') == 0
    assert recipe.get_amount_remaining(dest, 'stage 1', 'mL') == 50

def test_amount_remaining_stages_with_remove_plate(water, salt):
    recipe = Recipe()
    water_stock = Container('water stock', initial_contents=((water, '100 mL'),))
    source = Plate('source', '2 mL', rows=2, columns=2)
    dest = Plate('dest', '1 mL', rows=2, columns=2)
    recipe.uses(source, dest, water_stock)
    recipe.transfer(water_stock, source, quantity='2 mL')
    recipe.start_stage('stage 1')
    recipe.transfer(source, dest, quantity='1 mL')
    recipe.end_stage('stage 1')
    recipe.remove(dest, water)
    recipe.bake()
    expected = np.zeros((2, 2))
    assert pytest.approx(expected) == recipe.get_amount_remaining(dest, 'all', 'mL')
    expected = np.ones((2, 2))
    assert pytest.approx(expected) == recipe.get_amount_remaining(dest, 'stage 1', 'mL' )

