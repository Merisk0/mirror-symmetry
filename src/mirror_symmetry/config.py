# -*- coding: utf-8 -*-
"""用户设置持久化（窗口位置、上次使用的参数等）。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_DIR_NAME = "MirrorSymmetry"

DEFAULTS = {
    "mode": "lr_left",
    "split": 50.0,
    "scale": "100",
    "square": False,
    "bg": [255, 255, 255],
    "play": True,
    "geometry": "",
    "last_dir": "",
    "watermark": True,
    "watermark_text": "merisk.top",
    "window_max": False,
}


def config_dir() -> Path:
    """跨平台的配置目录。"""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home())
        path = Path(base) / APP_DIR_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        path = Path(base) / "mirror-symmetry"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return config_dir() / "settings.json"


def load_settings() -> dict:
    data = dict(DEFAULTS)
    try:
        raw = json.loads(settings_path().read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            for key, value in raw.items():
                if key in DEFAULTS:
                    data[key] = value
    except Exception:
        pass
    return data


def save_settings(data: dict) -> None:
    try:
        merged = dict(DEFAULTS)
        merged.update({k: v for k, v in data.items() if k in DEFAULTS})
        settings_path().write_text(
            json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass
