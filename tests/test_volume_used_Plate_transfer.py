from pyplate.pyplate import Plate, Container, Recipe


def test_transfer_between_plates(salt, water):
    plate1 = Plate('plate 1', max_volume_per_well='100 uL')
    plate2 = Plate('plate 2', max_volume_per_well='100 uL')
    source_container = Container('source', initial_contents=[(water, '100 mL')])

    recipe = Recipe().uses(source_container, plate1, plate2)
    recipe.transfer(source_container, plate1, quantity='50 uL')
    recipe.transfer(plate1, plate2, quantity='10 uL')
    recipe.bake()
