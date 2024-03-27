# from pyplate import Plate, Container, Recipe, Substance
# from pyplate.pyplate import PlateSlicer
#
# water = Substance.liquid('H2O', mol_weight=18.0153, density=1)
# source_container = Container('source', initial_contents=((water, '100 mL'),))
# dest_container = Container('dest')
#
# recipe = Recipe().uses(source_container, dest_container)
# recipe.start_stage('stage 1')
# recipe.transfer(source_container, dest_container, quantity='50 mL')
# recipe.end_stage('stage 1')
# recipe.remove(dest_container, water)
# recipe.bake()
# used = recipe.amount_used(water, destinations=[source_container], unit="mL")
# print(used)

from pyplate import  Substance, Recipe, Container
water = Substance.liquid('H2O', mol_weight=18.0153, density=1)
sodium_sulfate = Substance.solid('Sodium sulfate', 142.04)

recipe = Recipe()
dest_container = Container('dest_container', initial_contents=None)
recipe.uses(dest_container)

recipe.start_stage('stage 1')
stock_solution = recipe.create_solution(solute=sodium_sulfate, solvent=water, concentration='0.5 M', total_quantity='50 mL')
recipe.transfer(stock_solution, dest_container, '10 mL')
recipe.end_stage('stage 1')

recipe.start_stage('stage 2')
recipe.remove(dest_container, water)

# implicit end of stage at end of recipe
# recipe.end_stage('stage 2')

recipe.bake()

#Assertions
expected_amount = '25.0 mmol'
assert recipe.amount_used(substance=sodium_sulfate, timeframe='all', unit='mmol') == expected_amount
assert recipe.volume_used(container=dest_container, timeframe='all', unit= 'mL') == {"in": 50, "out": 0}