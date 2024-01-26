from typing import Union, Optional, List

from pyplate import Substance, Container
import itertools


class Factor:
    """"
    A factor is a variable that is under the control of the experimenter.
    It has a name (must be unique to a given experimental space), a list
    of possible values, and a verifier function.
    verifier takes a well object and a desired value and returns True if
    the well is consistent with the description.

    :param name: The name of the factor
    :type name: str
    :param possible_values: A list of possible values for the factor
    :type possible_values: list[str | Substance]
    :param verifier: A function that takes a well and a value and returns True if the well is consistent with the value
    :type verifier: callable
    """

    name: str
    possible_values: list[str | Substance]
    verifier: callable

    def __init__(self, name: str, possible_values: list[str | Substance], verifier: callable):
        self.name = name
        self.possible_values = possible_values
        self.verifier = verifier

    def __repr__(self):
        return f"Factor({self.name}, {self.possible_values}, {self.verifier})"

    def __str__(self):
        return f"Factor: {self.name} with possible values {self.possible_values}"

    def __eq__(self, other):
        return (self.name == other.name
                and self.possible_values == other.possible_values
                and self.verifier == other.verifier)

    def __hash__(self):
        return hash((self.name, tuple(self.possible_values), self.verifier))


class Experiment:
    """
    An experiment represents a single experiment within an experimental space. It has
    a dictionary of factors and their values. It's experiment_id is a unique identifier
    for the experiment within the experimental space. The replicate_idx distinguishes
    between multiple replicates of the same experiment. The well object is a reference
    to the well in which the experiment was performed.

    :param factors: A dictionary of factors and their values
    :type factors: dict
    :param experiment_id: A unique identifier for the experiment within the experimental space
    :type experiment_id: int
    :param replicate_idx: A unique identifier for the replicate of the experiment
    :type replicate_idx: int
    :param well: A reference to the well in which the experiment was performed
    :type well: Container
    """

    factors: dict[str, [str | Substance]]
    experiment_id: int
    replicate_idx: int
    well: Optional[Container]

    def __init__(self, factors: dict[str, [str | Substance]], experiment_id: int, replicate_idx: int,
                 well: Optional[Container] = None):
        self.factors = factors
        self.experiment_id = experiment_id
        self.replicate_idx = replicate_idx
        self.well = well

    def map_well(self, well: Container) -> None:
        """
        Map the experiment to a well. This is useful for keeping track of
        which well an experiment was performed in.

        :param well: The well to map to
        :type well: Container
        :return: None
        """
        self.well = well

    def __repr__(self):
        return f"Experiment({self.factors}, {self.experiment_id}, {self.replicate_idx}, {self.well})"

    def __str__(self):
        return (f"Experiment: {self.factors} "
                f"with experiment_id {self.experiment_id} "
                f"and replicate_idx {self.replicate_idx}")

    def __getitem__(self, key):
        return self.factors[key]

    def __setitem__(self, key, value):
        self.factors[key] = value

    def __contains__(self, key):
        return key in self.factors

    def __iter__(self):
        return iter(self.factors)

    def __len__(self):
        return len(self.factors)

    def __eq__(self, other):
        return (self.factors == other.factors
                and self.experiment_id == other.experiment_id
                and self.replicate_idx == other.replicate_idx
                and self.well == other.well)

    def __hash__(self):
        return hash((frozenset(self.factors.items()), self.experiment_id, self.replicate_idx, self.well))


class ExperimentalSpace:
    """
    An experimental space is a collection of experiments that share the same factors.
    It a list of factors, a list of blocks, and a list of all experiments. The blocks
    allow for grouping of experiments with similar fixed factors.

    :param factors: A set of factors that define the experimental space
    :type factors: set[Factor]
    :param experiment_id_generator: A function that generates unique experiment ids
    :type experiment_id_generator: callable
    """

    factors: set[Factor]
    blocks: list[Experiment]
    experiments: list[Experiment]
    blocks: Optional[list[Experiment]]
    experiments: Optional[list[Experiment]]

    def __init__(self, factors: set[Factor], experiment_id_generator: callable):
        self.factors = factors
        self.experiment_id_generator = experiment_id_generator
        self.blocks = None
        self.experiments = None

    def register_factor(self, factor: Factor) -> None:
        """
        Register a factor with the experimental space. Ensures that factor
        names are unique.

        :param factor: The factor to register
        :type factor: Factor
        :return: None
        """
        if factor in self.factors:
            raise ValueError(f"Factor {factor.name} already exists in experimental space")
        self.factors.add(factor)

    def add_experiment(self, experiment: Experiment) -> None:
        """
        Add an experiment to the experimental space. This is useful for manually
        adding experiments without `generate_experiments`.

        :param experiment: The experiment to add
        :type experiment: Experiment
        :return: None
        """
        if not self.experiments:
            self.experiments = []
        if experiment.factors.keys() != {x.name for x in self.factors}:
            raise ValueError(f"Experiment factors {experiment.factors.keys()}"
                             f" do not match experimental space factors {self.factors}")
        for factor_name in experiment.factors:
            factor_object = self.get_registered_factor(factor_name)
            if experiment[factor_name] not in factor_object.possible_values:
                raise ValueError(f"Experiment factor {factor_name} value {experiment[factor_name]}"
                                 f" not in possible values {factor_object.possible_values}")
        self.experiments.append(experiment)

    def filter_experiments(self, filter_function: callable) -> None:
        """
        Filter the experiments in the experimental space. This is useful for
        removing experiments that do not meet certain criteria.

        :param filter_function: A function that takes an experiment and returns True if it should be kept
        :type filter_function: callable
        :return: None
        """
        self.experiments = [x for x in self.experiments if filter_function(x)]

    def get_registered_factor(self, factor_name) -> Factor:
        """
        Get a registered factor by name.

        :param factor_name: The name of the factor to get
        :type factor_name: str
        :return: The factor object
        :rtype: Factor
        """
        for factor in self.factors:
            if factor.name == factor_name:
                return factor
        raise ValueError(f"Factor {factor_name} not found in experimental space")

    def generate_experiments(self, factors: dict[str, [str | Substance]],
                             n_replicates: int, blocking_factors: list[str]) -> list[list[Experiment]]:
        """
        Generate experiments for the experimental space. This is useful for
        generating a full factorial design of a subset of the experimental space.

        :param factors: A list of factors to generate experiments for (must be a subset of the experimental space factors)
        :type factors: dict[str, [str | Substance]]
        :param n_replicates: The number of replicates to generate for each experiment
        :type n_replicates: int
        :param blocking_factors: A list of factors to use for blocking
        :type blocking_factors: list[str]
        :return: A list of blocks, where each block is a list of experiments
        """
        filtered_factors = {}
        for factor in self.factors:
            if factors[factor.name] == "all":
                filtered_factors[factor.name] = factor.possible_values
            else:
                filtered_factors[factor.name] = [value for value in factor.possible_values if value in factors[factor.name]]
        
        # Initialize blocks
        blocks = {}

        """
        The following lines return a list of tuples shown below, assuming you block on Factor 1 and Factor 2:
        [
            [
                [("Factor 1", "value 1"), ("Factor 2", "value 1"), ("Factor 3", "value 1")],
                [("Factor 1", "value 1"), ("Factor 2", "value 1"), ("Factor 3", "value 2")],
            ],
            [
                [("Factor 1", "value 1"), ("Factor 2", "value 2"), ("Factor 3", "value 1")],
                [("Factor 1", "value 1"), ("Factor 2", "value 2"), ("Factor 3", "value 2")],
            ],
            ...
        ]
        
        Easy to use this to create dicts and thus experiments
        """

        # If needed form blocking combinations
        blocking_combinations = list(itertools.product(*[filtered_factors[name] for name in blocking_factors]))

        # Iterate over each combination of blocking factors
        for block_combination in blocking_combinations:
            block = []
            
            # Filter out the current blocking factors and create combinations of other factors
            non_blocking_factors = {name: values for name, values in filtered_factors.items() if name not in blocking_factors}
            other_combinations = list(itertools.product(*non_blocking_factors.values()))

            # Generate experiments for each combination
            for comb in other_combinations:
                factors_dict = dict(zip(non_blocking_factors.keys(), comb))
                
                # Set the values of the blocking factors
                for bf, value in zip(blocking_factors, block_combination):
                    factors_dict[bf] = value

                # Create replicates for each unique combination
                for rep in range(n_replicates):
                    experiment = Experiment(factors=factors_dict, replicate_idx=rep+1, experiment_id=self.experiment_id_generator())
                    block.append(experiment)

            # Use the blocking factor combination as the key for the blocks dictionary
            blocks[block_combination] = block

        return blocks
    
        #Another implementation
        # experiment_factor_values = {}
        # for factor in self.factors:
        #     if factors[factor.name] == "all":
        #         experiment_factor_values[factor.name] = factor.possible_values
        #     else:
        #         experiment_factor_values[factor.name] = [value for value in factor.possible_values if
        #                                                  value in factors[factor.name]]

        # non_blocking_factor_values = dict(filter(lambda x: x[0] not in blocking_factors, experiment_factor_values.items()))
        # blocking_factor_values = dict(filter(lambda x: x[0] in blocking_factors, experiment_factor_values.items()))

        # # Initialize blocks
        # blocks = []

        """
        The following lines return a list of tuples shown below, assuming you block on Factor 1 and Factor 2:
        [
            [
                [("Factor 1", "value 1"), ("Factor 2", "value 1"), ("Factor 3", "value 1")],
                [("Factor 1", "value 1"), ("Factor 2", "value 1"), ("Factor 3", "value 2")],
            ],
            [
                [("Factor 1", "value 1"), ("Factor 2", "value 2"), ("Factor 3", "value 1")],
                [("Factor 1", "value 1"), ("Factor 2", "value 2"), ("Factor 3", "value 2")],
            ],
            ...
        ]
        
        Easy to use this to create dicts and thus experiments
        """
        # blocking_factor_combos = [list(zip(blocking_factor_values.keys(), values)) for values in itertools.product(*blocking_factor_values.values())]
        # non_blocking_factor_combos = [list(zip(non_blocking_factor_values.keys(), values)) for values in itertools.product(*non_blocking_factor_values.values())]

        # for blocking_combo in blocking_factor_combos:
        #     block = []
        #     for non_blocking_combo in non_blocking_factor_combos:
        #         for rep in range(n_replicates):
        #             experiment = Experiment(dict(blocking_combo + non_blocking_combo), self.experiment_id_generator(), rep + 1)
        #             block.append(experiment)
        #     blocks.append(block)

        # return blocks
    

