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
        self.moles_prefix = yaml_config['moles_storage']
        assert self.moles_prefix[1:] == 'mol'
        self.volume_prefix = yaml_config['volume_storage']
        assert self.volume_prefix[1:] == 'L'
        self.solid_density = float(yaml_config['solid_density'])


config = Config()
