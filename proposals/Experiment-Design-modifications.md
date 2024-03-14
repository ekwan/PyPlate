Modifications to Factors:
An experiment may have more than one value for each factor.
When defining the space, you can specify a minimum and maximum number of factors.
Each factor has a flag for whether duplicates of a given value are allowed.

usage flow:

1. Define experimental space, factors, factor rules (two specific values for two factors may not be in same experiment)
user provides a function to check for rule consistency -- these are the factor rules.
2. Generate experiment enumeration (automatic or manual)
3. Verify that experiment enumeration is consistent with factor rules
4. Define recipe to implement experiments
5. Define mapping between Experiments and Containers, mapping goes both ways (unimplemented, but we assume it works)
6. Verify that results of recipe match all experiments within the enumeration 

# TODO: Pizza example for experiment design flow


Verifiers for Experiments: Check whether a Container implements that Experiment.
```python
solvent = Factor(water, dsmo)
solute = Factor(salt, triethylamine)

space = ExperimentalSpace(factors = [solvent, solute])

exp1 = Experiment(solvent.water, solute.salt)
well = Container(initial_contents=((water, 10 mL), (salt, 0.1 mol)))

exp1.verify()


```


Verifiers for Experimental Spaces: 
