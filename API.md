# PyPlate

Welcome to the design document for *PyPlate*.  Here, we lay out the intended purpose, conceptual basis, and expected behavior of the program.

## Introduction

The *PyPlate* Python API defines a set of objects and operations for implementing a high-throughput screen of chemical or biological conditions.  *PyPlate* assists with the enumeration of solid or liquid handling steps, ensures that those steps are physically reasonable, and provides plate visualization capabilities.

## Scope

*PyPlate* specifically focuses on the implementation of high-throughput experimentation (HTE).  The upstream process of designing the screens themselves will be handled elsewhere.  Similarly, the downstream process of analyzing the outcomes of screens will also be handled elsewhere.

## External Classes

Four simple HTE classes will be exposed to the user: `Substance`, `Container`, `Plate`, and `Recipe`.  *All classes are immutable.*  (An immutable object is one whose fields cannot be changed once it has been constructed.)

*Once recipe.bake() has been called, it should be immutable.*

---

### Substance

**Definition:** an abstract chemical or biological entity (e.g., reagent, enzyme, solvent, etc.).  Immutable.  Solids and enzymes are assumed to require zero volume.

**Constructors/Factory Methods:**

- Substance.solid(name, molecular_weight)
- Substance.liquid(name, molecular_weight, density)
- Substance.enzyme(name)

**Attributes:**

*we should support an optional `molecule` field of type `cctk.Molecule` and be able to infer the molecular weight from that*

*name (str):* name of the `Substance`
*type (int):* normal solid (1), liquid (2), enzyme solid (3)
*molecular_weight (float, optional):* in g/mol
*density (float, optional):* in g/mL
*molecule (cctk.Molecule, optional)*: the 3D structure

**Methods:**

*please fill in*

---

### Container

**Definition:** Stores specified quantities of `Substances` in a vessel with a given maximum volume.  Immutable.

**Constructors/Factory Methods:**

Container(name, max_volume, initial_contents) where initial_contents is an iterable of tuples of the form (substance,amount), with types `Substance` and `str`, respectively.

**Attributes:**

name (str): name of this Container
contents (dict): map from `Substances` to amounts (str?).
max_volume (float): in microlitres.

**Methods:**

- **copy():** Clones current `Container`
- **add(what, how_much):** Create a new `Container` with the additional `Substance`.  If `what` is already present, amounts should stack.  *Should we allow dictionaries here to add multiple substances?*
- **add_from(source_container, volume):** Move `volume` from `source_container` to here, decreasing the amount in `source_container` and increasing the amount in this object.  Note that all `Substances` should be transferred in proportion to their volumetric ratios (as pipettes are not Substance-selective!).  As `Containers` are immutable, this function returns `new_source_container` and `new_destination_container`. 

**Stacking:** What happens when we try to stack Substances with `add` or `add_from`?  My suggestion is that if they are in the same units, then stacking is allowed.  If they are in different units, then density/molecular_weight conversions must be possible.  Otherwise, throw an exception.

*Should there be a convenience method for performing a dilution?*

---

### Plate

**Definition:** A spatially ordered collection of `Containers`, like a 96 well plate.  The spatial arrangement must be rectangular.  Immutable.

**Constructors/Factory Methods:**

Plate(name, contents, n\_rows, n\_columns, row\_labels, column\_labels, max\_capacities)

**Attributes:**

name (str): name of this Container
contents (dict): map from `Substances` to amounts (str?).
n_rows (int): how many rows there are (default, 8)
n_cols (int): how many columns there are (default, 12)
row_labels (list of str): by default, A, B, C, ..., AA, AB, ...
column_labels (list of str): by default, "1", "2", ...
max_capacities (float): assumed to be the same volume for all wells, in uL

**Methods:**

- Plate[slice]
  - Returns a helper class (`PlateSlicer`) to help perform actions on slices *Shouldn't this return an iterable of `Containers`?  Or, are you saying that if we add something to the slice, the plate slicer will help return a new Plate with the updated Containers?*
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
  - *Is this a deep clone of all the Containers as well? I assume we don't need to clone all the Substances too?  Is cloning necessary with immutable objects?*

*Need to add concentrations method.*

**Stacking:**

We should provide methods for adding entire plates to other plates.  Should that be provided here or in Recipe?

### Recipe

**Definition:** A list of instructions for transforming one set of containers into another.  The intended workflow is to declare the source containers, enumerate the desired transformations, and call recipe.bake().  This method will ensure that all solid and liquid handling instructions are valid.  If they are indeed valid, then the updated containers will be generated.  Once recipe.bake() has been called, no more instructions can be added and the Recipe is considered immutable.

**Constructors/Factory Methods:**

Recipe(name, uses): creates a blank Recipe with the specified source `Containers`.

**Attributes:**

name (str): a short description
uses (list): a list of *Containers* that will be used in this `Recipe`.  An exception will be thrown if an attempt is made to use an undeclared Container.  A warning will be given if a declared Container is not used at "baking time."

**Methods:**

- **uses(*containers)**
  - declare `*containers` (iterable of `Containers`) as 
- **transfer(source_containers, destination_containers, amount)**
  - transfer `amount` (specified in volume units) from each `source_container` to each `destination_container`
  - the shape of `source_containers` and `destination_containers` must be compatible (*please list the cases: one to one, many to one, one to many, and many to many*)
- ~~create\_container(name, max\_volume, initial\_contents)~~
  - **Why did we think we needed this method again?**
  - Adds a step that creates a container as above and adds it to the used list.
  - Returns new container so that it can be used later in the same recipe.
- **bake()**
  - Checks the validity of each step and ensures all Containers are used.
  - Returns all new Containers and Plates in the order they were defined in `uses()`.

*Need to add some visualization and instruction printing methods.


## Internal Classes

These classes will not be exposed to the user.

### PlateSlicer

*Please explain the concept here.  Please also update the below to match the style and detail of the above.*

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

## Supported Units

The following SI base units are used:

- moles: `123 mol`
- enzyme activity units `123 U`
- mass: `123 g`
- millilitres: `123 L`

Each unit can be modified with the following prefixes:

- `k` for kilo (1E3): `123 kg`
- `m` for milli (1E-3): `123 mU`
- `u` for micro (1E-6): `123 uL`
- `n` for nano (1E-9): `123 nmol`

## Slicing

Inspired by `numpy` and `pandas`, wells (`Containers`) in plates can be addressed either by numerical index or string label.  Numerical indices start at 1.  By default, string labels also start at `"1"` or `"A"`.  Range slices are always inclusive on both ends of the interval.  The type of label is automatically inferred via variable type.

Here are some examples for a standard 96 well plate, with rows A-H and columns 1-12:

- well B3: `plate["B3"]`, `plate[2,3]`, `plate["B",3]`,  `plate[2,"3"]`, `plate["B","3"]`
- selecting row C: `plate["C",:]`, `plate[3,:]`
- selecting column 5: `plate[:,5]`
- rectangular selections with ranges: `plate["B":"C",3:5]`, `plate["B3":"C5"]` (*there doesn't seem to be a logical way to use numeric indices with the second form?*)
- strides: plate["A",::2] would select A1, A3, A5, A7, A9, and A11.
- custom selections with lists: plate[["A1","B5","A3"]]

## Example Workflow

*Please update/fill out.  I suggest you write out Joe Parry's design workflow in the new paradigm.*

```
from PyPlate import Substance, Container, Recipe, Generic96WellPlate

water = Substance.liquid('H2O', mol_weight=18.0153, density=1)
salt = Substance.solid('NaCl', 58.4428)

salt_water_halfM = Container('halfM salt water')
recipe = Recipe().uses(water, salt, salt_water_halfM)
recipe.transfer(water, salt_water_halfM, '100 mL')
recipe.transfer(salt, salt_water_halfM, '50 mmol')
salt_water_halfM, = recipe.build()

# recipe = Recipe()
# recipe.create_container('halfM salt water', ((water, '100 mL'), (salt, '50 mmol')))
# # recipe.transfer('halfM salt water', plate[:2], '1 uL')
# salt_water_halfM = recipe.build()


salt_water_oneM = Container('oneM salt water')
recipe2 = Recipe().uses(water, salt, salt_water_oneM)
recipe2.transfer(water, salt_water_oneM, '100 mL')
recipe2.transfer(salt, salt_water_oneM, '100 mmol')
salt_water_oneM, = recipe2.build()

recipe3 = Recipe().uses(salt_water_halfM, salt_water_oneM)
recipe3.transfer(salt_water_halfM, salt_water_oneM, '5 mL')
salt_water_halfM, salt_water_oneM = recipe3.build()

plate = Generic96WellPlate('plate', 50_000.0)
recipe4 = Recipe().uses(plate, salt_water_oneM, salt_water_halfM)
recipe4.transfer(salt_water_oneM, plate[:4], '0.5 mL')
recipe4.transfer(salt_water_halfM, plate, '0.5 mL')
plate, salt_water_oneM, salt_water_halfM = recipe4.build()

recipe5 = Recipe().uses(plate, salt_water_oneM)
for sub_plate, volume in {plate[1, 1]: 1.0, plate['A', 2]: 2.0, plate[1, 3]: 3.0,
                          plate[3, 3]: 7.0, plate['D', 3]: 10.0, plate[5, '3']: 9.0}.items():
    recipe5.transfer(salt_water_oneM, sub_plate, f"{volume} uL")
plate, salt_water_oneM = recipe5.build()

print(plate.volumes())
print(plate.substances())
print(salt_water_halfM)
print(salt_water_oneM)
# for recipe in [recipe, recipe2, recipe3, recipe4, recipe5]:
#     print(recipe)
#     print('=========')

# salt_water_oneM.volume = 100
# import numpy
# print(numpy.vectorize(lambda elem: elem.container.contents)(plate.wells))
# recipe6 = Recipe().uses(salt, plate)
# result = recipe6.do_transfer(salt, plate[:3, :3], '1 g')
# result = recipe6.do_transfer(salt, plate[3:6, 3:6], '10 g')
# print(numpy.vectorize(lambda elem: elem.container.contents)(plate.wells))
```



