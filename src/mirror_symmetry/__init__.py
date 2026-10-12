# -*- coding: utf-8 -*-
"""对称表情包生成器 —— 把图片 / GIF 从中间切开镜像成对称图。"""

from . import watermark  # noqa: F401
from .watermark import make_payload, read_watermark  # noqa: F401
from .core import (  # noqa: F401
    MODES,
    MODE_LABEL,
    MODE_RADIO,
    CUT_MODES,
    make_symmetric,
    load_frames,
    save_gif,
    save_webp,
    fit_square,
    flatten_to_rgb,
    export_frames,
)

__version__ = "2.3.0"
__all__ = [
    "__version__",
    "MODES",
    "MODE_LABEL",
    "MODE_RADIO",
    "CUT_MODES",
    "make_symmetric",
    "load_frames",
    "save_gif",
    "save_webp",
    "fit_square",
    "flatten_to_rgb",
    "export_frames",
    "watermark",
    "make_payload",
    "read_watermark",
]


