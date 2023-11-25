
# Proposal for PyPlate Experimental Design

## Factor

Represents an experimental condition that is under the experimenter's control.

### Instance Variables:

- `name`: A string representing the name of the factor, must be unique within an Experimental Space.

- `possible_values`: A list of strings, numerics, or Substances representing the possible values of the factor.

- `verifier`: A function that takes a Well object and a possible value. It returns a boolean value if the contents of the well match the desired value provided. Verify provided value is in `possible_values`.

## Experiment

Represents a single experiment.

### Instance Variables:

- `factors`: A dictionary with factor names as keys and corresponding values.

- `experiment_id`: Some arbitrary identifier for the experiment, may be auto generated or specified by the user.

- `replicate_idx`: An identifier to distinguish between repeated experiments with the same factors, by default is `experiment_id-{numeric idx starting from 1}`. 

- `well`: A pointer to the `Well` an experiment corresponds to

### Methods

-`map_well(Well)`: Maps a given `Well` to this `Experiment`.


## ExperimentalSpace

Represents the experimental space, including fixed and variable factors.  

### Instance Variables:

- `factors`: A list of Factor objects representing the fixed factors in the experimental space.

- `blocks`: A dictionary with names as keys and values as lists containing experiments representing the generated experiments.
-`experiments`: A list of all experiments registered with the space
- `experiment_id_generator`: A function that returns an identifier for a given Experiment in the space. The function will take in an `Experiment` object, and return a string that will serve as the ID for a given experiment.

### Methods:

- `generate_experiments(fixed_factors, variable_factors, n_replicates, blocking_factors)`: Fully enumerates the tree of variable factors, generates experiments with well/plate indices that respect blocking rules, and stores them in the instance variable. `n_replicates` is number of replicates to be generated. If experiments with this combination of factors exist, `n_replicants` is the number of *additional* replicates to generated. `blocking_factors` is a list of sets of factor names to block on (analogous to `GROUP BY` in SQL). The groups are a factorial enumeration of the `blocking_factors`. Automatically adds all experiments to the space.

- `is_valid(Experiment)`: Checks if a given experiment is valid. If `generate_experiments` has run, simply checks if the experiment is in the list. Otherwise, manually checks if values are in a Factor's possible values.

- `add_experiment(Experiment)`: Manually adds an experiment to the space. Checks for validity

  

## Example Usage

```python
coupling_type = Factor("coupling_type", ["Cross Electrophile", "Negishi", "Suzuki"])
catalyst_1_CE = Factor("catalyst 1 CE", ["Ni"])
catalyst_2_CE = Factor("catalyst 2 CE", ["Pd"])
reductant_CE = Factor("reductant CE", ["Zn"])
temperature_CE = Factor("temperature CE", [60])
solvent_CE = Factor("solvent CE", "DMF")
XY_Identity_CE = Factor("XY Identity CE", ["R1OTf+R2Cl", "R1OTf+R2Br", "R1Cl+R2OTf", "R1Br+R2OTf", "R1OTf+R2OTs", "R1OTs+R2OTf"])
Product_CE = Factor("Product CE", [...])
N_Ligand_CE = Factor("N Ligand CE", ["dtbbpy", "dbrbpy", "ttbtpy", "iminophosphorance"])
P_Ligand_CE = Factor("P Ligand CE", ["dppp", "dppb"])
Additive_CE = Factor("Additive CE", ["LiCl", "KF", "KBr"])

temperature_SZ = Factor("temperature SZ", [100])
XY_Identity_SZ = Factor("XY Identity SZ", ["R1Cl+R2Bpin", "R2Cl+R2MIDA", "R1BPin+R2Cl", "R1MIDA+R2Cl"])
Products_SZ = Factor("Products SZ", [...])
Pd_Ligand_Precomplex_SZ = Factor("Pd Ligand Precomplex SZ", ["Xphos", "SPhos", "P(tBu)3", "PCy3", "PPh3"])
Bases_SZ = Factor("Bases SZ", ["K3PO4", "Cs2CO3"])
Solvent_SZ = Factor("Solvent SZ", ["1,4-dioxane H2O", "DMF H2O"])
Additive_SZ = Factor("Additive SZ", ["CuCl", "Cu(AOc)2"])

temperature_NG = Factor("temperature NG", [60])
zincation_source_NG = Factor("zincation source NG", ["iPrMgCl+ZnCl2"])
XY_Identity_NG = Factor("XY Identity NG", ["R1ZnCl+R2Cl", "R1ZnCl+R2Br", "R1Cl+R2ZnCl", "R1BrR2ZnCl"])
Products_NG = Factor("Products NG", [...])
Pd_ligand_precomplexes_NG = Factor("Pd-ligand precomplexes NG", ["XPhos", "SPhos", "P(tBu)3", "RuPhos", "PPh3"])
solvents_NG = Factor("solvents NG", ["THF", "THF:NMP(1:1)"])
additives_NG = Factor("additives NG", ["LiCl", "LiBr"])

# The ... represent adding the rest of the factors for the experiment
exp_space = ExperimentalSpace(
	factors=[
	coupling_type,
	catalyst_1_CE,
	catalyst_2_CE,
	...
	,temperature_SZ,
	XY_identity_SZ,
	...,
	temperature_NG, 
	zincation_source_NG, 		
)

valid_experiment_CE = Experiment(factors = {
	"catalyst 1 CE": "Ni",
	"catalyst 2 CE": "Pd",
	"reductant CE": "Zn",
	"temperature CE": 60,
	"solvent CE": "DMF",
	"XY Identity CE": "R1OTf+R2Cl",
	"product CE": ..., 
	"N ligand CE":"dtbbpy",
	"P ligand CE": "dppp",
	"Additive CE": "LiCl"
	}
)

invalid_experiment_CE = Experiment(factors = {
	"catalyst 1 CE": "Ni",
	"catalyst 2 CE": "Pd",
	"reductant CE": "Zn",
	"temperature CE": 100,
	"solvent CE": "DMF",
	"XY Identity CE": "R1OTf+R2Cl",
	"product CE": ..., 
	"N ligand CE":"dtbbpy",
	"P ligand CE": "dppp",
	"Additive CE": "LiCl"
	}
)

valid_exp_sz = Experiment(factors = {
		"temperature SZ": 100, 
		"XY Identity SZ": "R1Cl+R2Bpin",
		"Products SZ": "...",
		"Pd Ligand Precomplex SZ": "Xphos",
		"Bases SZ": "K3PO4",
		"Solvent SZ": "1,4-dioxane H2O",
		"Additive SZ": "CuCl" 
	}
)

invalid_exp_sz = Experiment(factors = {
		"temperature SZ": 100, 
		"XY Identity SZ": "R1Cl+R2Bpin",
		"Products SZ": "...",
		"Pd Ligand Precomplex SZ": "Xphos",
		"Bases SZ": "K3PO4",
		"Solvent SZ": "THF", #invalid solvent
		"Additive SZ": "CuCl" 
	}
)

valid_exp_ng = Experiment(factors = {
		"temperature NG": 60,
		"zincation source NG": "iPrMgCl+ZnCl2",
		"XY Identity NG": "R1ZnCl+R2Cl",
		"Products NG": ...,
		"Pd-ligand precomplexes NG": "XPhos",
		"solvents NG": "THF",
		"additives NG": "LiCl"
	}
)

invalid_exp_ng = Experiment(factors = {
		"temperature NG": 60,
		"zincation source NG": "iPrMgCl+ZnCl2",
		"XY Identity NG": "R1ZnCl+R2Cl",
		"Products NG": ...,
		"Pd-ligand precomplexes NG": "CuPhos", #invalid precomplex
		"solvents NG": "THF",
		"additives NG": "LiCl"
	}
)

print(exp_space.is_valid(valid_experiment_ce)) # True
print(exp_space.is_valid(invalid_experiment_ce)) # False

print(exp_space.is_valid(valid_exp_sz)) # True
print(exp_space.is_valid(invalid_exp_sz)) # False

print(exp_space.is_valid(valid_exp_sz)) # True
print(exp_space.is_valid(invalid_exp_sz)) # False

negishi_blocks = exp_space.generate_experiments(
	fixed_factors = {
		coupling_type: "Negishi"
	},
	variable_factors = [
		temperature_NG,
		zincation_source_NG,
		XY_Identity_NG,
		Products_NG,
		Pd_ligand_precomplexes_NG, 
		solvents_NG,
		additives_NG
	]
	# all experiments are generated twice
	n_replicates = 2,
	blocking_factors = [{"coupling_type"}, {"N Ligand CE", "P Ligand CE"}, {"X Identity", "Y Identity"}]
)

print(cross_electrophile_block.experiments[0] == valid_exp_ng) # True
# The valid experiment is identical to the experiment we defined above
```
