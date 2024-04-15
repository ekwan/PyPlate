from pyplate.pyplate import Plate, Container, Recipe


def test_transfer_between_plates(salt, water):
    plate1 = Plate('plate 1', max_volume_per_well='100 uL')
    plate2 = Plate('plate 2', max_volume_per_well='100 uL')
    source_container = Container('source', initial_contents=[(water, '100 mL')])

    recipe = Recipe().uses(source_container, plate1, plate2)
    recipe.transfer(source_container, plate1, quantity='50 uL')
    recipe.transfer(plate1, plate2, quantity='10 uL')
    recipe.bake()

def test_2(salt, water):
    container = Container.create_solution(salt, water, concentration='1 M', total_quantity='100 mL')
    plate = Plate('plate', max_volume_per_well='100 uL')
    plate2 = Plate('plate2', max_volume_per_well='100 uL')
    recipe = Recipe().uses(container, plate, plate2)
    recipe.transfer(container, plate, quantity='50 uL')
    recipe.transfer(plate, plate2, quantity='10 uL')
    recipe.bake()
    assert recipe.substance_used(salt, 'all', 'mmol') == '100.0 mmol'
    # 50 umol * 96 = 4.8 mmol
    assert recipe.substance_used(salt, 'dispensing', 'mmol') == '4.8 mmol'
    # returns 4.8 mmol + 10 umol * 96 = 5.76 mmol
