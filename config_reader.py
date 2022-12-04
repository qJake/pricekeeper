import copy
import os
import json
from typing import Union
import yaml
from cerberus.validator import Validator, BareValidator

from types import SimpleNamespace

CFG_PATH = 'config.yaml'


def read_config() -> SimpleNamespace:
    return json.loads(json.dumps(read_config_dict()), object_hook=lambda d: SimpleNamespace(**d))


def read_config_dict(no_templates=False) -> SimpleNamespace:
    if not os.path.exists(CFG_PATH):
        print(f"Error: Config file not found. (Path={CFG_PATH})")
        return None

    with open(CFG_PATH, 'r') as s:
        try:
            cfg: dict = yaml.safe_load(s)
            if not no_templates:
                cfg = apply_templates(cfg)

            return cfg
        except Exception as ex:
            print(f"Error: Cannot deserialize config file. Is your YAML valid? ({ex})")
            return


def apply_templates(cfg: dict) -> dict:
    if 'rules' in cfg:
        for i, r in enumerate(cfg['rules']):
            if 'template' in r and 'templates' in cfg and r['template'] in cfg['templates']:
                r = r | cfg['templates'][r['template']]
            cfg['rules'][i] = r

    return cfg


def validate_config(cfg: dict) -> bool:
    cfg = apply_templates(cfg)
    with open('pricekeeper-schema.json', 'r') as sch:
        schema = json.load(sch)
    validator: BareValidator = Validator(schema)
    is_valid = validator.validate(cfg)
    if not is_valid:
        raise ConfigValidationException(list(f"{e}: {str(validator.errors[e])}" for e in validator.errors))
    return is_valid


class ConfigValidationException(Exception):
    """Raised when the configuration dictionary did not validate."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(errors[0])
        pass


def write_config_dict(newCfg: dict) -> bool:
    valCfg = copy.deepcopy(newCfg)
    validate_config(valCfg)

    try:
        with open(CFG_PATH, 'w') as s:
            s.write(yaml.dump(newCfg))
    except:
        return False

    return True


def yaml_to_dict(yml: str) -> dict:
    return yaml.safe_load(yml)


def get_yaml_rules() -> str:
    return _get_yaml_section('rules')


def get_yaml_templates() -> str:
    return _get_yaml_section('templates')


def _get_yaml_section(section: str) -> str:
    if not os.path.exists(CFG_PATH):
        print(f"Error: Config file not found. (Path={CFG_PATH})")
        return None

    with open(CFG_PATH, 'r') as s:
        try:
            yml = yaml.safe_load(s)

            if section in yml:
                return yaml.dump(yml[section])

            return ''

        except Exception as ex:
            print(f"Error: Cannot deserialize config file. Is your YAML valid? ({ex})")
            return '# ERROR - CHECK LOGS'


def merge_objects(s1: SimpleNamespace, s2: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(**s1.__dict__, **s2.__dict__)
