import json
import os

SETTINGS_PATH = os.path.expanduser("~/.config/metaai-desktop/settings.json")

DEFAULTS = {
    "window_width": 1100,
    "window_height": 750,
    "window_x": -1,
    "window_y": -1,
    "dark_mode": True,
    "zoom_level": 1.0,
}


def load() -> dict:
    try:
        with open(SETTINGS_PATH) as f:
            data = json.load(f)
        return {**DEFAULTS, **data}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULTS)


def save(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f, indent=2)
