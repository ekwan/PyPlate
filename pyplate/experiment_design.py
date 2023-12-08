from typing import Union, Optional

from pyplate import Substance, Container


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
        Register a factor with the experimental space. This is useful for keeping track
        """
        if factor.name in self.factors:
            raise ValueError(f"Factor {factor.name} already exists in experimental space")
        self.factors.add(factor)

    def add_experiment(self, experiment: Experiment) -> None:
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
        self.experiments = [x for x in self.experiments if filter_function(x)]

    def get_registered_factor(self, factor_name) -> Factor:
        for factor in self.factors:
            if factor.name == factor_name:
                return factor
        raise ValueError(f"Factor {factor_name} not found in experimental space")

    def generate_experiments(self, fixed_factors: list[Factor], variable_factors: list[Factor],
                             n_replicates: int, blocking_factors: list[set[Factor]]) -> None:
        #TODO: Implement stub
        """
        Generate the experiments for the experimental space. This is useful for generating
        a large number of experiments with a small number of factors.

        :param fixed_factors: A list of factors that are fixed across all experiments
        :type fixed_factors: list[Factor]
        :param variable_factors: A list of factors that vary across experiments
        :type variable_factors: list[Factor]
        :param n_replicates: The number of replicates for each experiment
        :type n_replicates: int
        :param blocking_factors: A list of sets factors that are blocked together. The
        order of the list determines the order of the blocks.
        :type blocking_factors: list[Factor]
        :return: None
        """
        pass