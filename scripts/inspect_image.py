#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查一张（或一文件夹的）导出图片里是否带有本工具的标记。

用法：
    python scripts/inspect_image.py 图片.png
    python scripts/inspect_image.py D:\某个文件夹
    python scripts/inspect_image.py 图片.gif --json

支持 PNG / JPG / WebP / GIF / BMP / TIFF。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mirror_symmetry import mark as mk  # noqa: E402

EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff"}


def describe(path: Path) -> dict | None:
    info = mk.read_mark(path)
    if not info:
        return None
    return {
        "file": str(path),
        "tag": info.get("text"),
        "time": info.get("time"),
        "size": info.get("size"),
        "signature": info.get("signature"),
        "carrier": info.get("method"),
        "raw": info.get("raw"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="检查图片里是否带有本工具的标记")
    parser.add_argument("path", help="图片文件或文件夹")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args()

    target = Path(args.path)
    files: list[Path]
    if target.is_dir():
        files = sorted(p for p in target.iterdir() if p.suffix.lower() in EXTS)
    elif target.is_file():
        files = [target]
    else:
        print(f"找不到：{target}")
        return 2

    results = []
    for f in files:
        results.append(describe(f))

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    hit = 0
    for path, info in zip(files, results):
        if info:
            hit += 1
            print(f"[有标记] {path.name}")
            print(f"    标签   : {info['tag']}")
            print(f"    时间   : {info['time']}")
            print(f"    尺寸   : {info['size']}")
            print(f"    指纹   : {info['signature']}")
            print(f"    载体   : {'像素最低位' if info['carrier'] == 'lsb' else '文件元数据'}")
        else:
            print(f"[无标记] {path.name}")
    print(f"\n共 {len(files)} 个文件，其中 {hit} 个带有标记。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
