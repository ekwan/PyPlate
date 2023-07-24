from PyPlate import Substance, Container, Generic96WellPlate

sodium_sulfate = Substance.solid("sodium sulfate", mol_weight=142.04)
triethylamine = Substance.liquid("triethylamine", mol_weight=101.19, density=0.726)

print(sodium_sulfate)
print(triethylamine)

water = Substance.liquid("H2O", mol_weight=18.0153, density=1)
water_DI = Container("DI water").transfer(water, '10 mL')
water_tap = Container("tap water").transfer(water, '20 mL')
dmso = Substance.liquid("DMSO", mol_weight=78.13, density=1.1004)
dmso_stock = Container("DMSO").transfer(dmso, '15 mL')
print(water_DI)
print(water_tap)
print(dmso_stock)


water_DI, sodium_sulfate_halfM = Container("Sodium sulfate 0.5M").transfer(water_DI, '10 mL')
sodium_sulfate_halfM = sodium_sulfate_halfM.transfer(sodium_sulfate, '0.5 M')
print(water_DI, sodium_sulfate_halfM)
print()

water_DI = Container("DI water").transfer(water, '10 mL')
water_DI, sodium_sulfate_halfM = Container("Sodium sulfate 0.5M").transfer(water_DI, '10 mL')
sodium_sulfate_halfM = sodium_sulfate_halfM.transfer(sodium_sulfate, '5 mmol')
print(water_DI, sodium_sulfate_halfM)


plate = Generic96WellPlate('plate', max_volume_per_well=500)
