import os
import yaml
from pathlib import Path

file_path = None
for path in [Path(os.environ.get('PYPLATE_CONFIG', '')), Path.home(), Path(os.path.dirname(__file__))]:
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

print(type(yaml_config))
print(yaml_config)