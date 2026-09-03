import os
import yaml


CONFIG_FILE = "jarvis_config.yaml"


def load_config():
    """
    Load Jarvis configuration.
    """

    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            "Jarvis configuration file not found."
        )

    with open(CONFIG_FILE, "r") as file:
        return yaml.safe_load(file)


config = load_config()

