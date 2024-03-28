from pathlib import Path
import os
import yaml


# import pyplate

class Config:
    def __init__(self):
        file_path = None

        for path in [Path(os.environ.get('PYPLATE_CONFIG', '')), Path.cwd().joinpath('..'), Path.home()]:
            path = path.joinpath('pyplate.yaml')
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
        self.moles_prefix = yaml_config['moles_storage']
        assert self.moles_prefix[1:] == 'mol'
        self.volume_prefix = yaml_config['volume_storage']
        assert self.volume_prefix[1:] == 'L'
        self.default_density = float(yaml_config['default_density'])
        self.default_weight_volume_units = yaml_config['default_weight_volume_units']
        self.default_moles_unit = yaml_config['default_moles_unit']
        self.default_volume_unit = yaml_config['default_volume_unit']
        self.default_colormap = yaml_config['default_colormap']
        self.default_diverging_colormap = yaml_config['default_diverging_colormap']
        self.precisions = yaml_config['precisions']


from .pyplate import Substance, Container, Plate, Recipe
