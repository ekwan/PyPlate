# PyPlate

Welcome to the design document for *PyPlate*.  Here, we lay out the intended purpose, conceptual basis, and expected behavior of the program.

## Introduction

The *PyPlate* Python API defines a set of objects and operations for implementing a high-throughput screen of chemical or biological conditions.  *PyPlate* assists with the enumeration of solid or liquid handling steps, ensures that those steps are physically reasonable, and provides plate visualization capabilities.

## Scope

*PyPlate* specifically focuses on the implementation of high-throughput experimentation (HTE).  The upstream process of designing the screens themselves will be handled elsewhere.  Similarly, the downstream process of analyzing the outcomes of screens will also be handled elsewhere.

## External Classes

Four simple HTE classes will be exposed to the user: `Substance`, `Container`, `Plate`, and `Recipe`.  *All classes are immutable.*  (An immutable object is one whose fields cannot be changed once it has been constructed.)

Note: all quantity, volume, and max_volume parameters are given as strings. For example, '10 mL', '5 g', '1 mol', or '11 U'.

The following are set based on preferences read `pyplate.yaml`:

  - Units in which moles and volumes are stored internally. `moles_storage` and `volume_storage`
  - Density of solids in g/mL. `solid_density`
  - Units for '%w/v' concentrations ('g/mL'). `default_weight_volume_units:`

---

### Substance

#### Definition: 
- An abstract chemical or biological entity (e.g., reagent, enzyme, solvent, etc.).  Immutable.  Solids and enzymes are assumed to require zero volume.

#### Constructors/Factory Methods

- Substance.solid(name, molecular_weight, molecule)
- Substance.liquid(name, molecular_weight, density, molecule)
- Substance.enzyme(name, molecule)

#### Attributes

- name (str): name of the `Substance`
- molecular_weight (float, optional): in g/mol
- density (float, optional): in g/mL
- molecule (cctk.Molecule, optional): the 3D structure

#### Methods
- is_liquid(): Return True if the `Substance` is a liquid.
- is_solid(): Return True if the `Substance` is a solid.
- is_enzyme(): Return True if the `Substance` is an enzyme.
---

### Container

#### Definition:

- Stores specified quantities of `Substances` in a vessel with a given maximum volume.  Immutable.

#### Constructors/Factory Methods:

- Container(name, max_volume, initial_contents) where initial_contents is an iterable of tuples of the form (substance,amount), with types `Substance` and `str`, respectively.

#### Attributes:

- name (str): Name of this Container
- contents (dict): map from `Substances` to amounts. Amounts are stored in liters for liquids, moles for solids, and activity units for enzymes
- max_volume (float): in storage format (determined by volume_storage from `pyplate.yaml`).

#### Methods

- evaporate():
  - Removes all liquids from this Container.
- dilute(solute, concentration, solvent, new_name)
  - Creates a new diluted solution with respect to `solute`
  - Concentration can be any of "0.1 M", "0.1 m", "0.1 g/mL", "0.01 umol/10 uL", "5 %v/v", "5 %w/v", "5 %w/w"
  - Name of new container is optionally set to `new_name`

#### Static Methods:

- add(source, destination, quantity):
  - Move the given quantity of the *source* substance to the *destination* container. A new copy of *destination* will be returned.
- transfer(source, destination, volume):
  - Move *volume* from *source* to *destination* container, returning copies of the objects with amounts adjusted accordingly.
  - Note that all `Substances` in the source will be transferred in proportion to their volumetric ratios.
  - *source* can be a container, a plate, or a slice of a plate.
- create_solution(solute, concentration, solvent, quantity)
  - Create a new container with the desired quantity and containing the desired concentration of `solute`.
  - Concentration can be any of "0.1 M", "0.1 m", "0.1 g/mL", "0.01 umol/10 uL", "5 %v/v", "5 %w/v", "5 %w/w"
  - If `solute` is a liquid, volumes will be calculated appropriately.

---

### Plate

#### Definition:

- A spatially ordered collection of `Containers`, like a 96 well plate.  The spatial arrangement must be rectangular.  Immutable.

#### Constructors/Factory Methods:

- Plate(name, max_volume_per_well, make, rows, cols)
  - name (str): name of this plate
  - max_capacities (str): assumed to be the same volume for all wells
  - make (str): name of this kind of plate
  - rows (int or list of str): Either how many rows there are or labels for the rows
  - cols (int or list of str): Either how many columns there are or labels for the columns
  - Row names default to "A", "B", ..., "AA", "AB", etc.
  - Column names default to "1", "2", etc.


#### Methods:

- Plate[slice]
  - Returns a slice of the plate.

- evaporate()
  - Evaporates all liquid from the plate
- volumes(substance, unit)
  - Returns a `numpy` array of used volumes
  - If given, volumes will be restricted to volumes of substance
  - If given, volumes will be given in unit, otherwise in uL
- substances()
  - Returns a set of all substances used
- moles(substance, unit)
  - Returns a `numpy` array of moles of given substance
  - If given, moles will be return in unit, otherwise, complete moles.
- concentrations(substance)

** Evaporate, volumes, substances, moles, and concentrations can all be called on a slice of the plate


#### Static Methods:

- add(source, destination, quantity): Move the given quantity of the *source* substance to the *destination* container. A new copy of *destination* will be returned.
- transfer(source, destination, volume): Move *volume* from *source* to *destination* plate or slice, returning copies of the objects with amounts adjusted accordingly.
  - Note that all `Substances` in the source will be transferred in proportion to their volumetric ratios.
  - *source* can be a container, a plate, or a slice of a plate.

---

### Recipe

#### Definition:
- A list of instructions for transforming one set of containers into another.  The intended workflow is to declare the source containers, enumerate the desired transformations, and call recipe.bake().  This method will ensure that all solid and liquid handling instructions are valid.  If they are indeed valid, then the updated containers will be generated.  Once recipe.bake() has been called, no more instructions can be added and the Recipe is considered immutable.

#### Constructors/Factory Methods:

Recipe(name, uses): creates a blank Recipe with the specified source `Containers`.

#### Attributes:

name (str): a short description
uses (list): a list of *Containers* that will be used in this `Recipe`.  An exception will be thrown if an attempt is made to use an undeclared Container.  A warning will be given if a declared Container is not used at "baking time."

#### Methods:

- uses(*containers)
  - declare `*containers` (iterable of `Containers`) as being used in the recipe.
- add(source, destination, quantity):
  - Adds a step to the recipe which will move the given quantity of the *source* substance to the *destination*.
- transfer(source, destination, volume):
  - Adds a step to the recipe which will move *volume* from *source* to *destination*.
  - Note that all `Substances` in the source will be transferred in proportion to their volumetric ratios.
- create_container(name, max_volume, initial_contents)
  - Keep track of steps to create container in recipe
  - Adds a step that creates a container as above and adds it to the used list.
  - Returns new container so that it can be used later in the same recipe.
- create_solution(solute, concentration, solvent, quantity, name)
  - Adds a step to the recipe with will create a new container with the desired quantity and containing the desired concentration of `saolute`.
  - If `solute` is a liquid, volumes will be calculated appropriately.
  - Concentration can be any of "0.1 M", "0.1 m", "0.1 g/mL", "0.01 umol/10 uL", "5 %v/v", "5 %w/v", "5 %w/w"
  - Returns new container so that it can be used later in the same recipe.
- dilute(destination, solute, concentration, solvent, new_name)
  - Adds a step to create a new container diluted to a certain `concentration` of `solute` from `destination`
  - Concentration can be any of "0.1 M", "0.1 m", "0.1 g/mL", "0.01 umol/10 uL", "5 %v/v", "5 %w/v", "5 %w/w"
  - Name of new container is optionally set to `new_name`
- evaporate(destination)
  - Adds a step to remove all liquids from destination
- bake()
  - Checks the validity of each step and ensures all Containers are used.
  - Returns all new Containers and Plates in the order they were defined in `uses()`.
  - Locks recipe from future changes

*Need to add some visualization and instruction printing methods.

## [Example Workflow](examples/Example.py)
