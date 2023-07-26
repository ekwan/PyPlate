
All classes except for Recipe are immutable. All work is done on copies of the original instances.

- Amounts can be volume ('10 mL'), mass ('10 g'), or enzyme activity units ('10 AU')

Recipe - a set of instructions for transforming containers/plates

## Functions
### Substance
An abstract chemical (without quantity, but having a molecular weight, name, and optional structure)
- solid(name, mol_weight) -> Substance
  - Creates a new solid
- liquid(name, mol_weight, density) -> Substance
  - Creates a new liquid
- enzyme(name) -> Substance
  - Creates a new enzyme
- copy()
  - Clones current `Substance`

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
  - Returns a helper class (`Slicer`) to help perform actions on slices
- volumes(arr = None)
  - arr defaults to all the wells in the plate.
    - Can be a numpy array or a `Slicer `instance
  - Returns a numpy array of used volumes
- copy()
  - Clones current Plate

### Recipe

- uses(*args)
  - `args` is an iterable of objects intended to be used in the recipe
- transfer(frm, to, amount)
  - Adds a step that transfers an amount of a mixture from `frm` to `to`
- add(frm, to, amount)
  - Adds a step that transfers an amount of a substance from `frm` to `to`
- create_container(name, max_volume, initial_contents)
  - Adds a step that creates a container as above and adds it to the used list.
- build()
  - performs steps described using above functions, returning all new Containers and Plates in the order they were defined in `used()`

