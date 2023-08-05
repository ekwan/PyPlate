# from PyPlate import Reagent, StockSolution, Solvent, Generic96WellPlate
from PyPlate import Substance, Container, Plate, Recipe

# testing #

# define reagents
print("reagents:")
sodium_sulfate = Substance.solid("sodium sulfate", mol_weight=142.04)
triethylamine = Substance.liquid("triethylamine", mol_weight=101.19, density=0.726)
print(sodium_sulfate)
print(triethylamine)
print()

# create solvents
print("solvents:")
water_DI = Substance.liquid("DI water", 18.0153, 1)
water_DI_stock = Container("DI water", max_volume=10, initial_contents=[(water_DI, "10 mL")])
water_tap = Substance.liquid("tap water", 18.0153, 1)
water_tap_stock = Container("tap water", max_volume=20, initial_contents=[(water_tap, "20 mL")])
DMSO = Substance.liquid("DMSO", 78.13, 1.1004)
DMSO_stock = Container("DMSO", max_volume=15, initial_contents=[(DMSO, "15 mL")])
print(water_DI)
print(water_tap)
print(DMSO)
print()

# create stocks
# concentrations in M
# volumes in M
print("stock solutions:")
sodium_sulfate_halfM = Container.create_stock_solution(sodium_sulfate, 0.5, solvent=water_DI, volume=10.0)
triethylamine_10mM = Container.create_stock_solution(triethylamine, 0.01, DMSO, volume=10.0)
triethylamine_50mM = Container.create_stock_solution(triethylamine, 0.05, DMSO, volume=10.0)
print(sodium_sulfate_halfM)
print(triethylamine_10mM)
print(triethylamine_50mM)
print()

# create plate
print("plate:")
plate = Plate("test plate", max_volume_per_well=500.0)
print(plate)

# add stuff to the plate
# volume in uL
recipe = Recipe().uses(plate, sodium_sulfate_halfM, triethylamine_10mM)
for k, v in {(1, 1): 1.0, ("A", 2): 2.0, (1, 3): 3.0, (3, 3): 7.0, ("D", 3): 10.0, (5, "3"): 9.0}.items():
    recipe.transfer(sodium_sulfate_halfM, plate[k], f"{v} uL")
for k, v in {"D:10": 1.0, (5, 10): 2.0, (5, "11"): 3.0}.items():
    recipe.transfer(triethylamine_10mM, plate[k], f"{v} uL")
# recipe.transfer(triethylamine_10mM, plate["D:10"], "20_000 uL")

plate, sodium_sulfate_halfM, triethylamine_10mM = recipe.bake()

print(plate.volumes())
print(sodium_sulfate_halfM)
# exit()

recipe2 = Recipe().uses(plate, triethylamine_10mM, water_DI_stock, DMSO_stock)
for i in range(1, plate.n_columns+1):
    recipe2.transfer(triethylamine_10mM, plate[1, i], f"{30 * i} uL")
recipe2.transfer(triethylamine_10mM, plate[6], "2 uL")
recipe2.transfer(triethylamine_10mM, plate[7:"H"], "7 uL")
recipe2.transfer(triethylamine_10mM, plate[:, "10"], "8 uL")
recipe2.transfer(triethylamine_10mM, plate[:, 11:12], "9 uL")

recipe2.transfer(water_DI_stock, plate[1:8], "20 uL")
recipe2.transfer(DMSO_stock, plate[:, 1:12], "1 uL")

plate, triethylamine_10mM, water_DI_stock, DMSO_stock = recipe2.bake()
print()

# print total volumes
print("volumes:")
print(plate.volumes())
print()

# print how much of each stock solution or solvent we used:
print("used volumes:")
for substance in plate.substances():
    if substance.is_liquid():
        print(f"{substance.name} : {plate.volumes(substance).sum() * 1000.0:.1f} uL")
print()

exit()

# print moles
print("micromoles:\n")
for i in range(len(plate.moles)):
    print(plate.reagents[i])
    print(plate.moles[i, :, :])
    print()
print()

# dump plate to excel
filename = "plate.xlsx"
plate.to_excel(filename)
