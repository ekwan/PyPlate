# Substance tracking
Substance usage may be in the context of just the recipe steps ("during") or recipe steps *and* prep ("before").

Special case for Plate (actually a PlateSlicer), and PlateSlicer, iterate over all containers in slice
Track quantity on substance level for this

## methods to modify:

"before" tracking:
- [ ] uses
- `bake`
  - [x] `create_container`
  - [ ] `create_solution`
  - [ ] `create_solution_from`
  - [ ] `dilute`
  - [ ] `fill_to`
  - [ ] `transfer`
  - [ ] `remove`

"during" tracking:
- `bake`
    - [ ] `create_solution_from` (only worried about source)
    - [ ] `dilute`
    - [ ] `fill_to`
    - [ ] `transfer`
    - [ ] `remove`
  


## method signature
- timeframe: "before", "during",
- substance: The substance to return the usage for
- unit: the unit to return volumes in, use YAML default if None
  - mL if liquid
  - mg if solid
  - mmol if enzyme

return type: str with quantity in mol, mmol, etc.

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

