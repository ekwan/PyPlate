from pyplate import Substance, Container, Recipe, Plate


water = Substance.liquid('H2O', mol_weight=18.0153, density=1)
salt = Substance.solid('NaCl', 58.4428)
triethylamine = Substance.liquid("triethylamine", mol_weight=101.19, density=0.726)

recipe = Recipe()
water_stock = recipe.create_container('water stock', 'inf L', [(water, '1000 mL')])
salt_source = recipe.create_container('salt source', 'inf L', [(salt, '1000 g')])
recipe.create_container('halfM salt water', '1 L', ((water, '100 mL'), (salt, '50 mmol')))
results = recipe.bake()
salt_water_halfM = results['halfM salt water']


water_stock_2 = Container('water stock', 'inf L', [(water, '1000 mL')])
salt_source_2 = Container('salt source', 'inf L', [(salt, '1000 g')])


salt_water_oneM = Container('oneM salt water', '1 L')
recipe2 = Recipe().uses(water_stock_2, salt_source_2, salt_water_oneM)
recipe2.transfer(water_stock, salt_water_oneM, '100 mL')
recipe2.transfer(salt_source, salt_water_oneM, '100 mmol')
results = recipe2.bake()
salt_water_oneM = results['oneM salt water']


recipe3 = Recipe().uses(salt_water_halfM, salt_water_oneM)
recipe3.transfer(salt_water_halfM, salt_water_oneM, '5 mL')
results = recipe3.bake()
salt_water_halfM, salt_water_oneM = results['halfM salt water'], results['oneM salt water']


plate = Plate('plate', '50 mL')
recipe4 = Recipe().uses(plate, salt_water_oneM, salt_water_halfM)
recipe4.transfer(salt_water_oneM, plate[:4], '0.5 mL')
recipe4.transfer(salt_water_halfM, plate, '0.5 mL')
results = recipe4.bake()
plate = results['plate']
salt_water_oneM = results['oneM salt water']
salt_water_halfM = results['halfM salt water']


recipe5 = Recipe().uses(plate, salt_water_oneM)
for sub_plate, volume in {plate[1, 1]: 1.0, plate['A', 2]: 2.0, plate[1, 3]: 3.0,
                          plate[3, 3]: 7.0, plate['D', 3]: 10.0, plate[5, '3']: 9.0}.items():
    recipe5.transfer(salt_water_oneM, sub_plate, f"{volume} uL")
results = recipe5.bake()
plate = results['plate']
salt_water_oneM = results['oneM salt water']


print(plate.get_volumes())
print(plate.get_substances())
print(salt_water_halfM)
print(salt_water_oneM)


recipe6 = Recipe()
results = recipe6.bake()
