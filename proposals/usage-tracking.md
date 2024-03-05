# Usage Tracking

Motivation: Keep track of materials/solutions used throughout an experiment. Recipes can become very complex, and usage
tracking functions offer convenience methods for determining appropriate quantities for various components of an 
experiment.

## Minimal Recipe

```python
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
```

## Substance-level Tracking

You've "used" something in a recipe once it has been moved to a destination. To find this, you compare what's in 
the destinations at the start and end over the stage you specify.

The amount used of a substance is defined as the delta of the quantities of a specific substance in some containers at
the start and end of a timeframe.

Timeframes are specified using recipe stages.

### Method signature
```python
def amount_used(self, substance: Substance, timeframe: str = 'all', unit: str = None, 
                destinations: Iterable[Container | Plate] | str = "plates")
```
- `substance`: The substance to measure  
- `timeframe`: The timeframe over which the deltas of the destinations should be compared  
- `destinations`: A list of `Containers` to be considered destinations. Alternatively, pass in `"plates"` to  consider all
plates to be destinations. By default, all plates are considered destinations.

### Default Units
Default units for substances are determined by their type:  
- solids: `g`  
- liquids: `mL`  
- enzyme: `U`  

### Example
Let us consider the minimal recipe:

**The recipe begins:**
- The recipe defines that it is using the `dest_container` Container

#### Stage 1:  
> Contents of containers at the start of Stage 1:  
> ```python
> dest_container: {water: "0 mmol", sodium_sulfate: "0 mmol"}
> stock_solution: {water: "0 mmol", sodium_sulfate: "0 mmol"}
>          trash: {water: "0 mmol", sodium_sulfate: "0 mmol"} 
> ```
1. The `stock_solution` container is created by creating 50 mL of a 0.5 M solution of `water` and `sodium_sulfate`

[//]: # (> Contents of containers:)

[//]: # (> ```python)

[//]: # (> stock_solution: {water: "2578 mmol", sodium_sulfate: "25 mmol"})

[//]: # (> dest_container: {water: "0 mmol", sodium_sulfate: "0 mmol"})

[//]: # (> ```)
2. 10 mL of the solution in `stock_solution` is transferred into `dest_container`. 
> Contents of containers at the end of Stage 1:
> ```python
> stock_solution: {water: "2063 mmol", sodium_sulfate: "20 mmol"}
> dest_container: {water: "515 mmol", sodium_sulfate: "5 mmol"}
>          trash: {water: "0 mmol", sodium_sulfate: "0 mmol"} 
> ```


#### Stage 2:

> Contents of containers at the beginning of Stage 2:
> ```python
> stock_solution: {water: "2063 mmol", sodium_sulfate: "20 mmol"}
> dest_container: {water: "515 mmol", sodium_sulfate: "5 mmol"}
>          trash: {water: "0 mmol", sodium_sulfate: "0 mmol"} 
> ```
1. All of the water in `dest_container` is removed.

> Contents of containers at the end of Stage 2:
> ```python
> stock_solution: {water: "2063 mmol", sodium_sulfate: "20 mmol"}
> dest_container: {water: "0 mmol", sodium_sulfate: "5 mmol"}
>          trash: {water: "515 mmol", sodium_sulfate: "0 mmol"} 
> ```

#### Example calls:
> How much sodium sulfate was used during the whole recipe if `dest_container` is our only destination?
> ```python
> recipe.amount_used(substance=sodium_sulfate, timeframe='all', unit='mmol', destinations=[dest_container])
> ```
> We compare the amount of `sodium_sulfate` in `dest_container` at the start of end of the recipe, and find that the
> delta between the two is `5 mmol`, which we then return.


> How much water was used during the whole recipe if `dest_container` is our only destination?
> ```python
> recipe.amount_used(substance=water, timeframe='all', unit='mmol', destinations=[dest_container])
> ```
> We compare the amount of `sodium_sulfate` in `dest_container` at the start of end of the recipe, and find that the
> delta between the two is `0 mmol`. However, `trash` is always an implicit destination that stores removed substances.
> If we look at the delta for `trash`, we see `515 mmol` of water. Thus, we sum the quantities and return `515 mmol`.


> How much sodium sulfate was used during `Stage 1`if `stock_solution` is our only destination?
> ```python
> recipe.amount_used(substance=water, timeframe='Stage 1', unit='mmol', destinations=[dest_container])
> ```
> We compare the amount of `sodium_sulfate` in `stock_solution` at the start and end of `Stage 1`, and find that the
> delta between the two is `25 mmol`, which we then return.
## Container-level Tracking

You may want to keep track of the flows of a given solution. i.e. How much of a container's content has gone out of
or into it.

Timeframes are specified using recipe stages as in substance-level tracking.
