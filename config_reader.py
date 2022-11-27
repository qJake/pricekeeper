import json
import os
import types
import yaml

from types import SimpleNamespace

CFG_PATH = 'config.yaml'

def read_config() -> SimpleNamespace:
    if not os.path.exists(CFG_PATH):
        print(f"Error: Config file not found. (Path={CFG_PATH})")
        return None

    with open(CFG_PATH, 'r') as s:
        try:
            yml = yaml.safe_load(s)
            config = json.loads(json.dumps(yml), object_hook=lambda d: SimpleNamespace(**d))

            # Apply templates
            for i, r in enumerate(config.rules):
                if hasattr(r, 'template') and hasattr(config, 'templates') and hasattr(config.templates, r.template):
                    r = merge_objects(r, config.templates.__dict__[r.template])
                config.rules[i] = r

            return config
        except Exception as ex:
            print(f"Error: Cannot deserialize config file. Is your YAML valid? ({ex})")
            return


def merge_objects(s1: SimpleNamespace, s2: SimpleNamespace) -> SimpleNamespace:
    return SimpleNamespace(**s1.__dict__, **s2.__dict__)
