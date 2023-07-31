## PyPlate

All classes except for Recipe cannot be modified. All work is done on copies of the original instances.

- Amounts can be volume ('10 mL'), mass ('10 g'), moles ('1 mol'), or enzyme activity units ('10 AU')

### Substance
An abstract chemical (without quantity, but having a molecular weight, name, and optional structure)
- solid(name, mol_weight) -> Substance
  - Creates a new solid
- liquid(name, mol_weight, density) -> Substance
  - Creates a new liquid
- enzyme(name) -> Substance
  - Creates a new enzyme


### Container
An unordered collection of (substance, quantity) pairs, with a maximum capacity (i.e., a container of substances)
- Container(name, max_volume, initial_contents)
  - initial_contents is an iterable of tuples, (`Substance`, amount)
- copy()
  - Clones current `Container`
- add(frm, amount)
  - Adds substance to Container, returning a new container
- transfer(frm, amount)
  - Moves amount from source container
  - Returns `new_frm, new_container`


### Plate
A spatially ordered collection of containers (e.g., a 96 well plate)

#### Generic96WellPlate shown

- Plate(name, max_volume_per_well)
- Plate[slice]
  - Returns a helper class (`PlateSlicer`) to help perform actions on slices
- volumes(arr = None)
  - arr defaults to all the wells in the plate
    - Can be a numpy array or a `PlateSlicer` instance
  - Returns a numpy array of used volumes
- substances(arr = None)
  - arr defaults to all the wells in the plate
  - Returns a set of all substances used
- moles(substance, arr = None)
  - arr defaults to all the wells in the plate
  - Returns a numpy array of moles of given substance
- copy()
  - Clones current `Plate`

### Recipe
A set of instructions for transforming containers/plates

- uses(*args)
  - `args` is an iterable of objects intended to be used in the recipe
- add(frm, to, amount)
  - Adds a step that adds an amount of a substance from `frm` to `to`
  - `to` can be Container, a Plate, or a PlateSlicer
- transfer(frm, to, amount)
  - Adds a step that transfers an amount of a mixture from `frm` to `to`
  - `frm` and `to` can be slices of plates.
- create_container(name, max_volume, initial_contents)
  - Adds a step that creates a container as above and adds it to the used list.
  - Returns new container so that it can be used later in the same recipe.
- build()
  - performs steps described using above functions, returning all new
        Containers and Plates in the order they were defined in `uses()`

### PlateSlicer
- get()
  - Returns a numpy array of selected elements
- set(values)
  - Replaces elements
- add(frm, how_much):
  - Adds an amount of a substance from `frm` into each element in current `PlateSlicer`
  - Returns a new copy of the plate
- transfer(frm, how_much):
  - Transfers an amount of a mixture from `frm` into each element in current `PlateSlicer`
  - Returns a new copy of `frm` and a new copy of the current plate
- transfer_slice(frm, how_much):
  - Transfers an amount of mixture from each elem in `frm` into each element in current `PlateSlicer`
  - Returns new copies of each of the plates
- copy()
  - Clones current `PlateSlicer`
- shape
  - Shape of elements
- size
  - Number of elements
