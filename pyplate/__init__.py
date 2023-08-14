from pathlib import Path
import os
import yaml


class Config:
    def __init__(self):
        file_path = None
        environ_path = Path(os.environ.get('PYPLATE_CONFIG', ''))
        if environ_path.is_dir():
            environ_path = environ_path / "pyplate.yaml"
        for path in [environ_path, Path("pyplate.yaml"), Path("../pyplate.yaml"), Path.home() / "pyplate.yaml"]:
            if path.is_file():
                file_path = path
                break

        if file_path is None:
            raise RuntimeError("pyplate.yaml not found.")

        try:
            with file_path.open('r') as config_file:
                yaml_config = yaml.safe_load(config_file)
        except yaml.YAMLError as exc:
            raise RuntimeError("Config file could not be read.") from exc

        self.internal_precision = yaml_config['internal_precision']
        self.external_precision = yaml_config['external_precision']
        self.volume_storage = Config.convert_prefix_to_multiplier(yaml_config['volume_storage'][:-1])
        self.moles_storage = Config.convert_prefix_to_multiplier(yaml_config['moles_storage'][:-3])

    @staticmethod
    def convert_prefix_to_multiplier(prefix: str) -> float:
        """

        Converts an SI prefix into a multiplier.
        Example: "m" -> 1e-3, "u" -> 1e-6

        Arguments:
            prefix:

        Returns:
             Multiplier (float)

        """
        if not isinstance(prefix, str):
            raise TypeError("SI prefix must be a string.")
        prefixes = {'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3, 'c': 1e-2, 'd': 1e-1, '': 1, 'k': 1e3, 'M': 1e6}
        if prefix in prefixes:
            return prefixes[prefix]
        raise ValueError(f"Invalid prefix: {prefix}")


config = Config()
