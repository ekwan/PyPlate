from typing import Union, Optional

from pyplate import Substance, Container


class Factor:
    """"
    A factor is a variable that is under the control of the experimenter.
    It has a name (must be unique to a given experimental space), a list
    of possible values, and a verifier function.
    """

    def __init__(self, name: str, possible_values: list[Union[str, Substance]], verifier: callable):
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
    """

    def __init__(self, factors: dict, experiment_id: int, replicate_idx: int, well: Optional[Container] = None):
        self.factors = factors
        self.experiment_id = experiment_id
        self.replicate_idx = replicate_idx
        self.well = well

    def map_well(self, well: type[Container]):
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
    """

    def __init__(self, factors: set[Factor], experiment_id_generator: callable):
        self.factors = factors
        self.experiment_id_generator = experiment_id_generator
        self.blocks = None
        self.experiments = None

    def register_factor(self, factor: Factor):
        if factor.name in self.factors:
            raise ValueError(f"Factor {factor.name} already exists in experimental space")
        self.factors.add(factor)

    def add_experiment(self, experiment: Experiment):
        if not self.experiments:
            self.experiments = []
        if experiment.factors.keys() != {x.name for x in self.factors}:
            raise ValueError(f"Experiment factors {experiment.factors.keys()}"
                             f" do not match experimental space factors {self.factors}")
        for factor in experiment.factors:
            if experiment[factor] not in factor.possible_values:
                raise ValueError(f"Experiment factor {factor} value {experiment[factor]}"
                                 f" not in possible values {factor.possible_values}")
        self.experiments.append(experiment)
