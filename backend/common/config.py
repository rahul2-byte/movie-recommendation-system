import re
from pathlib import Path

import yaml
from dotmap import DotMap


class ConfigLoader:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config = DotMap()
        self._load_configs()
        self._interpolate_paths()

    def _load_configs(self):
        # Load all .yml files in the config directory
        for yml_file in self.config_dir.glob("*.yml"):
            with open(yml_file, "r") as f:
                data = yaml.safe_load(f)
                if data:
                    # Use the filename (without extension) as the key
                    self.config[yml_file.stem] = DotMap(data)

    def _interpolate_paths(self):
        # Interpolate ${...} placeholders across system.yml, including nested keys.
        if "system" not in self.config:
            return

        var_pattern = re.compile(r"\$\{([^}]+)\}")

        def lookup(root, path):
            current = root
            for part in path.split("."):
                if isinstance(current, DotMap) and part in current:
                    current = current[part]
                elif isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current

        def interpolate_string(value, root, max_passes=5):
            result = value
            for _ in range(max_passes):
                changed = False

                def repl(match):
                    nonlocal changed
                    key = match.group(1)
                    replacement = lookup(root, key)
                    if replacement is None or not isinstance(replacement, str):
                        return match.group(0)
                    changed = True
                    return replacement

                result = var_pattern.sub(repl, result)
                if not changed:
                    break
            return result

        def walk(node, root):
            if isinstance(node, DotMap) or isinstance(node, dict):
                for key in list(node.keys()):
                    node[key] = walk(node[key], root)
                return node
            if isinstance(node, list):
                return [walk(item, root) for item in node]
            if isinstance(node, str):
                return interpolate_string(node, root)
            return node

        # Mutate system config in-place so nested values can reference each other.
        walk(self.config.system, self.config.system)


# Initialize the global config object
# Assuming this file is at backend/utils/config.py
CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"
config_loader = ConfigLoader(CONFIG_DIR)
config = config_loader.config

# Import and attach settings.py
try:
    from configs import settings
    config.settings = settings
except ImportError:
    # Fallback if configs.settings isn't directly importable (e.g. during some tests)
    import sys
    sys.path.append(str(CONFIG_DIR.parent))
    from configs import settings
    config.settings = settings
