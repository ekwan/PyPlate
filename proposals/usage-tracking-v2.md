by default containers are sources (implicit), plates are destinations, pass in dictionary at recipe creation time to override

only track dispensing steps for destination objects

recipe stages: Define stages for a recipe that allow us to define custom timeframes/collections of recipe steps that start and end
    Must end stage before another stage starts
    Implicit end_stage at the end of a recipe
    examples:
        - recipe.start_stage("stage1")
        - recipe.transfer()
        - recipe.create_solution()
        - recipe.end_stage("stage1")
        - recipe.amount_used(substance, timeframe="stage1")

timeframes: defaults of "all" and "dispensing", recipe stages determine custom timeframes

## implementation:
    move substance tracking steps to post-bake
    recipe.remove() moves substances to an internal "removed" container that always acts as a destination


    timeframe:
        

## no remove step
recipe = Recipe()
container1 = recipe.create_container(initial_contents=(water, "10mL"))
plate1 = recipe.create_plate()
plate2 = recipe.create_plate()

recipe.transfer(source=container1, dest=plate1, volume="1mL")
recipe.transfer(source=plate1, dest=plate2, volume="1mL")
recipe.amount_used(water, unit="mL")


timeframe = "entire recipe", destination containers are [plate1, plate2]:
    recipe.amount_used(water, unit="mL") should return "1mL"
    because 1mL of water total is in all of the destination containers 

timeframe = "entire recipe", destination containers are [plate1]:
    recipe.amount_used(water, unit="mL") should return "0mL"

    because 0mL of water total is in all of the destination containers,
    plate2 does contain 1mL but it's not a destination so we don't care



## with remove step
recipe = Recipe()
container1 = recipe.create_container(initial_contents=(water, "10mL"))
plate1 = recipe.create_plate()
plate2 = recipe.create_plate()

recipe.transfer(source=container1, dest=plate1, volume="2mL")
recipe.start_stage("stage1")
recipe.transfer(source=plate1, dest=plate2, volume="1mL")
recipe.remove(what=water, container=plate2)
recipe.end_stage("stage1")
recipe.bake()
recipe.amount_used(water, unit="mL")

timeframe = "entire recipe", destination containers are [container1, plate1, plate2, __trash]:
recipe.amount_used(water, unit="mL") should return "10mL"

    because 10mL of water total is in all of the destination containers 
    "container1" contains 8mL, plate1 contains 1mL, and plate2 contain 0mL, _trash contains 1mL.

timeframe = "entire recipe", destination containers are [plate1, plate2, __trash]:
    recipe.amount_used(water, unit="mL") should return "2mL"

    because 2mL of water total is in all of the destination containers 
    "trash" contains 1mL, plate1 contains 1mL, and plate2 contain 0mL.

timeframe = "entire recipe", destination containers are [plate1, __trash]:
    recipe.amount_used(water, unit="mL") should return "2mL"

    because 1mL of water total is in all of the destination containers 
    "trash" contains 1mL, plate1 contains 1mL

timeframe = "stage1", destination containers are [plate1, plate2, __trash]:
    recipe.amount_used(water, timeframe="stage1", unit="mL") should return "0mL"


    start of stage1:
        container1: 8mL
        plate1:     2mL
        plate2:     0mL
        _trash:     0mL

    end of stage1:
        container1: 8mL
        plate1:     1mL
        plate2:     0mL
        _trash:     1mL

    because 2mL of water total is in all of the destination containers at the start of stage1
    **and**
    because 2mL of water total is in all of the destination containers at the end of stage1

