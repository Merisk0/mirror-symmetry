# -*- coding: utf-8 -*-
"""把程序打包成单文件 Windows 应用（dist/MirrorSymmetry.exe）。

用法:
    python scripts/build_exe.py
需要:
    pip install -e .[build]      # 会安装 PyInstaller
"""

import subprocess
import sys
from pathlib import Path

# Windows CI 的控制台不是 UTF-8，中文 print 会抛 UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
NAME = "MirrorSymmetry"


def make_icon() -> Path | None:
    sys.path.insert(0, str(SRC))
    try:
        from mirror_symmetry import theme

        path = theme.icon_path()
        if path and path.exists():
            return path
    except Exception as exc:
        import traceback
        print("[!] icon generation failed, using default icon")
        traceback.print_exc()
    return None


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("需要先安装 PyInstaller：\n    python -m pip install --upgrade pyinstaller")
        return 1

    icon = make_icon()
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        NAME,
        "--paths",
        str(SRC),
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build"),
        "--specpath",
        str(ROOT / "build"),
    ]
    if icon:
        args += ["--icon", str(icon)]
    args.append(str(ROOT / "scripts" / "entry.py"))

    print("[*] " + " ".join(args))
    result = subprocess.run(args, cwd=str(ROOT))
    if result.returncode == 0:
        exe = ROOT / "dist" / f"{NAME}.exe"
        size = exe.stat().st_size / 1024 / 1024 if exe.exists() else 0
        print(f"[+] 打包完成：{exe}  （{size:.1f} MB）")
        print("[*] 自检： " + str(exe) + " --selftest")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())


