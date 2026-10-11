#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""兼容入口：直接双击 / python mirror_symmetry.py 也能启动。

真正的代码在 src/mirror_symmetry/ 包里。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mirror_symmetry.ui import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
