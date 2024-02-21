# Substance tracking
#TODO: reword this
Substance usage may be in the context of when the containers are first used ("during") or before they are used ("before").

Two phases:
Prep: before any containers are used
Dispensing: after containers are used

Usage is defined as calling any of the methods below on a Recipe.
- `create_solution_from`
- `dilute`
- `transfer`
- `remove`

Special case for Plate (actually a PlateSlicer), and PlateSlicer, iterate over all containers in slice
Track quantity on substance level for this

## methods to modify:

"all" tracking:
- [x] `uses`
- `bake`
    - [x] `create_container`
    - [x] `create_solution`
    - [x] `create_solution_from` (only worried about solvent going in to destination) (no plates)
    - [x] `fill_to`
    - [x] `dilute` (account for *additional* solvent added to container)

"dispensing only" tracking:
- `bake`
    - [x] `create_solution_from` (only worried about source) (no plates)
    - [x] `dilute`
    - [x] `transfer`
  


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


## methods to test:
Track volume on container level for this

Special case for Plate (actually a PlateSlicer), and PlateSlicer, iterate over all containers in slice

"all" tracking:
- [ ] `uses`
- `bake`
    - [ ] `create_container`
    - [ ] `create_solution`
    - [ ] `create_solution_from` (only worried about solvent going in to destination) (no plates)
    - [ ] `fill_to`
    - [ ] `dilute` (account for *additional* solvent added to container)

"dispensing only" tracking:
- `bake`
    - [ ] `create_solution_from` (only worried about source) (no plates)
    - [ ] `dilute`
    - [ ] `transfer`


## notes
keep track of first use for containers for custom starting point.
{
"container": Used? (flip on create_solution_from, transfer)
}



QOL method for Recipe that returns a list of steps that involves a specific container.

- container: The container to search for
def get_steps_using(self, container):

