# Amount Usage Tracking

## Modes:
- `before`: Substances used to prepare for the entire experiment, accounts for substances not used in the steps of the experiment, but still used in the experiment.
- `during`: Substances used during the experiment, accounts for substances used in the steps of the experiment.
- `container`: Container level inflow and outflow level tracking, accounts for substances used in the steps of the experiment.

## Usage Tracking
Recipe objects have a `amount_used` method with the following signature. container is an optional parameter that defaults to `None`, only meant to be used when `mode='container'`.
```python
def amount_used(self, mode, container)
```

### `before` tracking
For every container, track all additions from outside the experiment. This includes the following steps:
- `create_container`
- `create_solution`
- `create_solution_from`
- `dilute`
- `fill_to`

Modify each method above to update a `before` dictionary in the recipe with the following structure:
```python
{
    substance: {
        "in": amount ,
        "out": amount
    }
}
```

### `during` tracking
For every container, track all substances moved from container to container within the experiment. This includes the following steps:
- `transfer`
- `remove`

Modify each method above to update a `during` dictionary in the recipe with the following structure:
```python
{
    substance: {
        "in": amount ,
        "out": amount
    }
}
```

### `container` tracking
For every container, track all substances moved into and out of the container. This includes every step in a recipe that modifies the amount of a substance in a container. This includes the following steps:

Meant to track usage for a given stock solution.

Modify each method above to update a `container` dictionary in the recipe with the following structure:
```python
{
    container: {
        substance: {
            'in': amount,
            'out': amount
        }
    }
}
```

## QOL Methods
- Provide a method to return the difference of in/out for each container.
- Provide a method to return the difference of before/during each substance.







Want to query either Substance or Container.


# Substance tracking
Substance usage may be in the context of just the recipe steps ("during") or recipe steps *and* prep ("before").

Special case for Plate (actually a PlateSlicer), and PlateSlicer, iterate over all containers in slice
Track quantity on substance level for this
"before" tracking:
- `uses`
- `bake`
    - `create_container`
    - `create_solution`
    - `create_solution_from`
    - `dilute`
    - `fill_to`
    - `transfer`
    - `remove`

"during" tracking:
- `bake`
    - `create_solution_from` (only worried about source)
    - `dilute`
    - `fill_to`
    - `transfer`
    - `remove`
  


## method signature
- timeframe: "before", "during",
- substance: The substance to return the usage for
- unit: the unit to return volumes in, use YAML default if None
  - mL if liquid
  - mg if solid
  - mmol if enzyme

def amounts_used(substance, timeframe="during", unit=None)


## notes
QOL method to return all substances used in a Recipe. Returns a set of substances.
- timeframe: "before", "during"
 
def substances_used(self, timeframe="before"):


# Volume Tracking
Query how much volume of a specific Container has been used.
Default behavior ("first use"): 
    t=0, volume is defined is defined as the volume of the container right before the first transfer out of it
    endpoint is end of recipe

Custom starting point:
    t=0, user specifies which step to start counting usage at, will be at a step that occurs after what the default behavior would pick
    endpoint is end of recipe

## method signature
- what: the Container or Plate to track
- timeframe: "default", or a specific RecipeStep
- unit: the unit to return volumes in, use YAML default if None

if container, return volume used
if plate, return dataframe with volume in each cell

def volume_used(self, what, timeframe="first_use", unit=None)


## methods to modify:
Track volume on container level for this

Special case for Plate (actually a PlateSlicer), and PlateSlicer, iterate over all containers in slice

- `uses`
- `bake`
    - `create_container`
    - `create_solution`
    - `create_solution_from`
    - `dilute`
    - `fill_to`
    - `transfer`
    - `remove`

## notes
keep track of first use for containers for custom starting point.
{
"container": Used? (flip on create_solution_from, transfer)
}



QOL method for Recipe that returns a list of steps that involves a specific container.

- container: The container to search for
def get_steps_using(self, container):


#TODO:
Make three simple recipes, write a unit test for these recipes, make sure you can pass them