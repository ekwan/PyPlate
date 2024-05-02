import numpy as np
from pyplate.pyplate import Recipe, Container, Substance
import pytest


def test_simple_volume_used(salt_water, water):
    container = Container('container', initial_contents=[(water, '20 mL')])
    recipe = Recipe()
    recipe.uses(salt_water, container)
    recipe.transfer(salt_water, container, '10 mL')
    #recipe.transfer
    recipe.bake()
    
    #Assertions
    assert recipe.get_substance_used(container, 'all', 'mL') == 100

def test_container_flows(sodium_sulfate, water):
    
    recipe = Recipe()
    dest_container = Container('dest_container', initial_contents=None)
    recipe.uses(dest_container)

    stock_solution = recipe.create_solution(solute=sodium_sulfate, 
                                            solvent=water, concentration='0.5 M', total_quantity='50 mL')
    recipe.start_stage('stage 1')
    recipe.transfer(stock_solution, dest_container, '10 mL')
    recipe.end_stage('stage 1')

    recipe.start_stage('stage 2')
    recipe.remove(dest_container, water)

    # implicit end of stage at end of recipe
    # recipe.end_stage('stage 2')

    recipe.bake()

    assert recipe.get_container_flows(container=stock_solution, 
                                      timeframe='all', unit='mL') == {"in": 50, "out": 10}
    assert recipe.get_container_flows(container=dest_container, timeframe='stage 2', unit='mL') == {"out": 9.278, "in": 0}
    