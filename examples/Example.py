from PyPlate import Substance, Container, Recipe, Generic96WellPlate

water = Substance.liquid('H2O', mol_weight=18.0153, density=1)
salt = Substance.solid('NaCl', 58.4428)

salt_water_halfM = Container('halfM salt water')
recipe = Recipe().uses(water, salt, salt_water_halfM)
recipe.transfer(water, salt_water_halfM, '100 mL')
recipe.transfer(salt, salt_water_halfM, '50 mmol')
salt_water_halfM, = recipe.build()

salt_water_oneM = Container('oneM salt water')
recipe2 = Recipe().uses(water, salt, salt_water_oneM)
recipe2.transfer(water, salt_water_oneM, '100 mL')
recipe2.transfer(salt, salt_water_oneM, '100 mmol')
salt_water_oneM, = recipe2.build()

recipe3 = Recipe().uses(salt_water_halfM, salt_water_oneM)
recipe3.transfer(salt_water_halfM, salt_water_oneM, '5 mL')
salt_water_halfM, salt_water_oneM = recipe3.build()

plate = Generic96WellPlate('plate', 50.0)
recipe4 = Recipe().uses(plate, salt_water_oneM, salt_water_halfM)
recipe4.transfer(salt_water_oneM, plate[:4], '1 mL')
recipe4.transfer(salt_water_halfM, plate, '1 mL')
plate, salt_water_oneM, salt_water_halfM = recipe4.build()

recipe5 = Recipe().uses(plate, salt_water_oneM)
for sub_plate, volume in {plate[1, 1]: 1.0, plate['A', 2]: 2.0, plate[1, 3]: 3.0,
                          plate[3, 3]: 7.0, plate['D', 3]: 10.0, plate[5, '3']: 9.0}.items():
    recipe5.transfer(salt_water_oneM, sub_plate, f"{volume} mL")
plate, salt_water_oneM = recipe5.build()

for recipe in [recipe, recipe2, recipe3, recipe4, recipe5]:
    print(recipe)
    print('=========')

# salt_water_oneM.volume = 100
# import numpy
# print(numpy.vectorize(lambda elem: elem.container.contents)(plate.wells))
# recipe6 = Recipe().uses(salt, plate)
# result = recipe6.do_transfer(salt, plate[:3, :3], '1 g')
# result = recipe6.do_transfer(salt, plate[3:6, 3:6], '10 g')
# print(numpy.vectorize(lambda elem: elem.container.contents)(plate.wells))
