# Usage Tracking

- PyPlate offers the ability to see how much of a given Substance or Container has been used at different stages of a Recipe
TODO: split into intro page, along with 3 pages for each method
TODO: in intro page, explain that there are 3 methods and explain when to use each method/give an example, separate pages for each method
- Substance-level tracking reports how much of a particular Substance has been used during a particular Recipe timeframe
- Container-level tracking monitors the flow of all materials in and out of a given Container during a particular Recipe timeframe
- 

## Minimal Recipe
In the following examples we will consider this recipe:

```python
from pyplate import Substance, Recipe, Container

water = Substance.liquid('H2O', mol_weight=18.0153, density=1)
sodium_sulfate = Substance.solid('Sodium sulfate', 142.04)

recipe = Recipe()
container = recipe.create_container('container', initial_contents=None)

stock_solution = recipe.create_solution(solute=sodium_sulfate, solvent=water, concentration='0.5 M',
                                        total_quantity='50 mL')

recipe.start_stage('stage 1')
recipe.transfer(stock_solution, container, '10 mL')
recipe.end_stage('stage 1')

recipe.start_stage('stage 2')
recipe.remove(container, water)

# implicit end of stage at end of recipe
recipe.end_stage('stage 2')

recipe.bake()
```
- The "all" stage begins at the start of the recipe and lasts until the end of the recipe
- A stage can be started with `recipe.start_stage` and it keeps track of steps that are performed until `recipe.end_stage` is called or the end of the recipe, whichever comes first
- Because stage 2 ends with the end of the recipe in the example above, `recipe.end_stage('stage 2')` is redundant
 

## Substance-level Tracking

- In this tracking mode, we must define a set of Containers and/or Plates as the destinations
- A Substance is considered "used" once it has been moved to the destination or removed with `recipe.remove` e.g. a solvent being evaporated
- When calling `recipe.remove`, the substance is considered to be moved to a special trash container, which is always considered a destination
- If no destinations are explicitly specified, all Plates are considered to be destinations
- Usage is defined as the net increase of the amount of a given substance in the destinations during a specified timeframe
- A timeframe begins/ends at the start/end of the given recipe stage or the start/end of the entire recipe
- If the amount of the substance in the destinations undergoes a net decrease during the timeframe, an error is thrown

### How to use `substance_used()`:
```python
def substance_used(self, substance: Substance, timeframe: str = 'all', unit: str = None, 
                destinations: Iterable[Container | Plate] | str = "plates")
```
- `substance`: The Substance to track
- `timeframe`: The timeframe over which the net difference should be calculated
- `unit`: The unit to return usage in
- `destinations`: A list of `Containers` and/or `Plates` to be considered destinations. Alternatively, pass in `"plates"` to  consider all
plates to be destinations. By default, all plates are considered destinations.
- Default units for substances are determined by their type:  
    - solids: `g`  
    - liquids: `mL`  
    - enzyme: `U`  


### Example calls:
> How much sodium sulfate was used during the whole recipe if `container` is our only destination?
 ```python
 recipe.substance_used(substance=sodium_sulfate, timeframe='all', unit='mmol', destinations=[container])
 ```
- We compare the amount of `sodium_sulfate` in `container` at the beginning and end of the recipe
- There are `0 mmol` at the beginning and `5 mmol` at the end
- The net difference for `container` is `5 mmol`, which is our "amount used"

  

> How much water was used during the whole recipe if `container` is our only destination?
 ```python
 recipe.substance_used(substance=water, timeframe='all', unit='mmol', destinations=[container])
 ```
-  We compare the amount of water in `container` at the beginning and end of the recipe
- There are `0 mmol` of water in `container` at the beginning of the recipe and `0 mmol` of water in `container` at the end of the recipe
- The net difference for `container` is `0 mmol`. 
- However, trash is always an implicit destination that stores removed substances.
- The amount of water in `trash` increases by `515 mmol` during the recipe
- Thus, we sum the two amounts and return `515 mmol`


> How much sodium sulfate was used during `Stage 1`if `stock_solution` is our only destination?
 ```python
 recipe.substance_used(substance=sodium_sulfate, timeframe='Stage 1', unit='mmol', destinations=[stock_container])
 ```
 - We compare the amount of sodium sulfate in `stock_solution` at the beginning and end of `Stage 1`
 - During this during stage 1 we transfer `10 ml` from `stock_solution` to `container`
 - But since `stock_solution` is specified as a destination, and there is a net decrease of `5 mmol` of sodium sulfate
 - Logically, it would make sense for `stock_solution` to be considered a source and not a destination
 - Thus, `amount_used` throws an error
 
### Recipe Walkthrough
The contents of all containers in the example recipe during different timeframes are shown below:
#### Start of Recipe:
 ```python
      container: {water: "0 mmol", sodium_sulfate: "0 mmol"}
stock_solution: {water: "0 mmol", sodium_sulfate: "0 mmol"}
          trash: {water: "0 mmol", sodium_sulfate: "0 mmol"} 
 ```
#### Stage 1 (start):
 ```python
container: {water: "2578 mmol", sodium_sulfate: "25 mmol"}
stock_solution: {water: "0 mmol", sodium_sulfate: "0 mmol"}
trash: {water: "0 mmol", sodium_sulfate: "0 mmol"} 
 ```
#### Stage 1 (end):
 ```python
stock_solution: {water: "2063 mmol", sodium_sulfate: "20 mmol"}
container: {water: "515 mmol", sodium_sulfate: "5 mmol"}
trash: {water: "0 mmol", sodium_sulfate: "0 mmol"} 
 ```


#### Stage 2 (start):
 ```python
stock_solution: {water: "2063 mmol", sodium_sulfate: "20 mmol"}
container: {water: "515 mmol", sodium_sulfate: "5 mmol"}
trash: {water: "0 mmol", sodium_sulfate: "0 mmol"} 
 ```
#### Stage 2 (end):
 ```python
stock_solution: {water: "2063 mmol", sodium_sulfate: "20 mmol"}
container: {water: "0 mmol", sodium_sulfate: "5 mmol"}
trash: {water: "515 mmol", sodium_sulfate: "0 mmol"} 
 ```


## Container Tracking
- In this mode, we track the change in the volume/mass/quantity of a given Container across a specific timeframe
- We assume that no additional material is added to the Container during the given stage
- This may be used to track the usage of a mixture, rather than a single substance
- Usage is defined as the net decrease in the volume/mass/quantity
 
todo: note about how calculations are done in mL
todo: enzyme edge case for activity units (U), enzymes "quantity" is measured in activity units, not mols

### How to use `get_volume_change()`
```python
def get_volume_change(container: Container | Plate, timeframe, str='all', unit: str | None = None)
```
- `container`: The container to get the volume for
- `timeframe`: The timeframe from which to get the volume
- `unit`: The unit to return the volume in

### Example calls:
TODO: Add calls for non-volume measurements

> How much stock_solution was used during stage 1?
```python
recipe.get_intermediate_volume(container=dest_container, timeframe='stage 1', unit='mL')
```
- The volume of `stock_solution` at the start of `Stage 1` is `50 mL`
- The volume of `stock_solution` at the end of `Stage 1` is `40 mL`
- Thus, the net difference, or usage, is `10 mL`

> How much stock_solution was used during stage 2?
```python
recipe.get_intermediate_volume(container=dest_container, timeframe='stage 2', unit='mL')
```
- The volume of `stock_solution` at the start of `Stage 2` is `40 mL`
- The volume of `stock_solution` at the end of `Stage 2` is `40 mL`
- Thus, the net difference, or usage, is `0 mL`

### Recipe Walkthrough
#### Start of Recipe:
#### Stage 1 (start):
Flows of containers at the start of Stage 1:
```
container: 0 mL
stock_solution: 50 mL
```
#### Stage 1 (end):
Contents of containers at the end of Stage 1:
```python
container: 10 mL
stock_solution: 40 mL
```

#### Stage 2 (start):
Contents of containers at the beginning of Stage 2:
```python
container: 10 mL
stock_solution: 40 mL
```

#### Stage 2 (end):
Contents of containers at the end of Stage 2:
```python
dest_container: 0.7221 mL
stock_solution: 40 mL
```

## Container-flow Tracking
- In this tracking mode, we track the volume flowing in and out of a given Container during a specific timeframe
- This may be used to track the usage of a solution, rather than a single substance
- Timeframes are specified using recipe stages as in substance-level tracking

### How to use `get_container_flows()`
```python
def get_container_flows(container: Container | Plate, timeframe: str = 'all', unit='uL': str | None = None)
```
- `container`: The container to get flows for
- `timeframe`: The timeframe over which the deltas of the destinations should be compared
- `unit`: The unit to return flows in


### Example calls:
> What are the flows for `stock_solution` across the entire recipe?
```python
recipe.get_container_flows(container=stock_solution, timeframe='all', unit='mL')
```
We take the difference of the flows of `stock_solution` at the beginning and end of the recipe and return the
dictionary. The difference of the outflows is `10 mL` and the difference of the inflows is `50 mL`.

This returns: `{"in": 50, "out": 10}`

> What are the flows for `dest_container` across `Stage 2`?
```python
recipe.get_container_flows(container=dest_container, timeframe='stage 2', unit='mL')
```
- We take the difference of the flows of `dest_container` at the beginning and end of the recipe and return the
dictionary. The difference of the outflows is `9.279 mL` and the difference of the inflows is `0 mL`.

### Recipe Walkthrough
#### Start of Recipe:
```python
container: {in: "0 mL", out: "0 mL"}
stock_solution: {in: "0 mL", out: "0 mL"}
```
#### Stage 1 (start):
Flows of containers at the start of Stage 1:
```python
dest_container: {in: "0 mL", out: "0 mL"}
stock_solution: {in: "50 mL", out: "0 mL"}
```

#### Stage 1 (end):
Contents of containers at the end of Stage 1:
```python
dest_container: {in: "10 mL", out: "0 mL"}
stock_solution: {in: "50 mL", out: "10 mL"}
```



#### Stage 2 (start):
Contents of containers at the beginning of Stage 2:
```python
dest_container: {in: "10 mL", out: "0 mL"}
stock_solution: {in: "50 mL", out: "10 mL"}
```
#### Stage 2 (end):
Contents of containers at the end of Stage 2:
```python
dest_container: {in: "10 mL", out: "9.2779 mL"}
stock_solution: {in: "50 mL", out: "10 mL"}
```

