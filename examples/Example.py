from PyPlate import Substance, Container, Generic96WellPlate, Recipe

sodium_sulfate = Substance.solid("sodium sulfate", mol_weight=142.04)
triethylamine = Substance.liquid("triethylamine", mol_weight=101.19, density=0.726)
dmso = Substance.liquid("DMSO", mol_weight=78.13, density=1.1004)
water = Substance.liquid("H2O", mol_weight=18.0153, density=1)
dmso_stock = Container("DMSO")
water_DI = Container("DI water")
water_tap = Container("tap water")
sodium_sulfate_halfM = Container("Sodium sulfate 0.5M")

recipe = Recipe()
recipe.uses(water, water_DI, water_tap, sodium_sulfate, sodium_sulfate_halfM)
recipe.transfer(water, water_DI, '10 mL').transfer(water, water_tap, '20 mL')
recipe.transfer(water_DI, sodium_sulfate_halfM, '8 mL').transfer(sodium_sulfate, sodium_sulfate_halfM, '5 mmol')
water, water_DI, water_tap, sodium_sulfate, sodium_sulfate_halfM = recipe.build()
print(water_DI)
print(water_tap)
print(sodium_sulfate_halfM)
# print(recipe.results)
# print(recipe.steps)
# print(recipe.build())
# water_DI = Container("DI water").transfer(water, '10 mL')
# water_tap = Container("tap water").transfer(water, '20 mL')
#
# dmso_stock = Container("DMSO").transfer(dmso, '15 mL')
# print(water_DI)
# print(water_tap)
# print(dmso_stock)
#
#
# water_DI, sodium_sulfate_halfM = Container("Sodium sulfate 0.5M").transfer(water_DI, '10 mL')
# sodium_sulfate_halfM = sodium_sulfate_halfM.transfer(sodium_sulfate, '0.5 M')
# print(water_DI, sodium_sulfate_halfM)
# print()
#
# water_DI = Container("DI water").transfer(water, '10 mL')
# water_DI, sodium_sulfate_halfM = Container("Sodium sulfate 0.5M").transfer(water_DI, '10 mL')
# sodium_sulfate_halfM = sodium_sulfate_halfM.transfer(sodium_sulfate, '5 mmol')
# print(water_DI, sodium_sulfate_halfM)
#
#
# plate = Generic96WellPlate('plate', max_volume_per_well=500)
