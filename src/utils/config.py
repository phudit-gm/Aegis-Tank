"""Load config/settings.yaml and config/protocol_contract.yaml as plain dicts."""

from pathlib import Path
import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def load_settings() -> dict:
    with open(CONFIG_DIR / "settings.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_protocol_contract() -> dict:
    with open(CONFIG_DIR / "protocol_contract.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
