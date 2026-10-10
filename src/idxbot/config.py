"""Membaca file config/settings.yaml."""
from pathlib import Path

import yaml

# Folder utama proyek (dua tingkat di atas folder idxbot)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"


def load_settings() -> dict:
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_db_path(settings: dict) -> Path:
    return PROJECT_ROOT / settings["data"]["database_path"]
