# -*- coding: utf-8 -*-
"""现代化平面主题：配色、ttk 样式、窗口图标。"""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageDraw

# --------------------------------------------------------------------------- #
#  配色（浅色现代风格）
# --------------------------------------------------------------------------- #
BG = "#F4F5F8"          # 窗口底色
CARD = "#FFFFFF"        # 卡片
CARD_ALT = "#FAFAFC"    # 次级卡片
BORDER = "#E6E8EF"      # 描边
BORDER_STRONG = "#D5D8E3"
TEXT = "#1B1F2A"        # 主文字
TEXT_MUTED = "#7A8194"  # 次要文字
TEXT_FAINT = "#A8AEBD"

ACCENT = "#6C5CE7"      # 主色（紫）
ACCENT_HOVER = "#5B4BD6"
ACCENT_SOFT = "#EFECFE"  # 主色浅底
SUCCESS = "#12B886"     # 保存/成功
SUCCESS_HOVER = "#0EA271"
DANGER = "#F0506E"
CANVAS_BG = "#FFFFFF"

FONT_FALLBACKS = (
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "微软雅黑",
    "PingFang SC",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "SimHei",
    "Segoe UI",
    "Helvetica Neue",
    "Arial",
)


def pick_font_family(root) -> str:
    try:
        families = set(tkfont.families(root))
    except Exception:
        return "TkDefaultFont"
    for name in FONT_FALLBACKS:
        if name in families:
            return name
    return "TkDefaultFont"


def font(size: int = 10, weight: str = "normal"):
    return ("Microsoft YaHei UI", size, weight)


def apply_theme(root: tk.Tk, lang: str = "zh", ui_scale: float = 1.0) -> dict:
    """给窗口套上现代平面主题，返回字体信息。

    英文字面看起来比中文小，所以英文界面整体字号大一号；
    ``ui_scale`` 是菜单里的界面缩放（1.0 = 100%）。
    """
    family = pick_font_family(root)
    english = str(lang).lower().startswith("en")
    try:
        scale = max(0.75, min(2.0, float(ui_scale or 1.0)))
    except Exception:
        scale = 1.0

    def grow(value: int) -> int:
        return max(8, int(round(value * scale)))

    size_base = grow(13 if english else 12)
    size_small = grow(12 if english else 11)
    size_title = grow(15 if english else 14)
    size_app = grow(18 if english else 16)
    style = ttk.Style(root)
    for name in ("clam", "default"):
        try:
            style.theme_use(name)
            break
        except Exception:
            continue

    base = (family, size_base)
    small = (family, size_small)
    title = (family, size_title, "bold")
    app = (family, size_app, "bold")
    root.option_add("*Font", base)
    root.configure(bg=BG)

    style.configure(".", font=base, background=BG, foreground=TEXT)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("Alt.TFrame", background=CARD_ALT)
    style.configure("Bar.TFrame", background=CARD)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT)
    style.configure("CardMuted.TLabel", background=CARD, foreground=TEXT_MUTED, font=small)
    style.configure("BarTitle.TLabel", background=CARD, foreground=TEXT, font=app)
    style.configure("BarSub.TLabel", background=CARD, foreground=TEXT_MUTED, font=small)
    style.configure("Section.TLabel", background=CARD, foreground=TEXT, font=title)
    style.configure("Hint.TLabel", background=CARD, foreground=TEXT_MUTED, font=small)
    style.configure("Chip.TLabel", background=ACCENT_SOFT, foreground=ACCENT, font=small,
                    padding=(8, 2))
    style.configure("Status.TLabel", background=BG, foreground=TEXT_MUTED, font=small)

    # 通用按钮（描边）
    style.configure(
        "Ghost.TButton",
        background=CARD,
        foreground=TEXT,
        bordercolor=BORDER_STRONG,
        focusthickness=0,
        focuscolor=CARD,
        relief="flat",
        padding=(12, 7),
    )
    style.map(
        "Ghost.TButton",
        background=[("pressed", "#F0F1F6"), ("active", "#F6F7FA"), ("disabled", CARD_ALT)],
        foreground=[("disabled", TEXT_FAINT)],
        bordercolor=[("active", BORDER_STRONG)],
    )

    # 主按钮
    style.configure(
        "Primary.TButton",
        background=ACCENT,
        foreground="#FFFFFF",
        bordercolor=ACCENT,
        focusthickness=0,
        focuscolor=ACCENT,
        relief="flat",
        padding=(14, 8),
    )
    style.map(
        "Primary.TButton",
        background=[("pressed", ACCENT_HOVER), ("active", ACCENT_HOVER), ("disabled", "#C9C4F2")],
        foreground=[("disabled", "#FFFFFF")],
        bordercolor=[("active", ACCENT_HOVER)],
    )

    # 成功按钮
    style.configure(
        "Success.TButton",
        background=SUCCESS,
        foreground="#FFFFFF",
        bordercolor=SUCCESS,
        focusthickness=0,
        focuscolor=SUCCESS,
        relief="flat",
        padding=(14, 8),
    )
    style.map(
        "Success.TButton",
        background=[("pressed", SUCCESS_HOVER), ("active", SUCCESS_HOVER), ("disabled", "#B6E3D3")],
        bordercolor=[("active", SUCCESS_HOVER)],
    )

    # 分段选择器（用 Toolbutton 样式做 chip 效果）
    style.configure(
        "Seg.Toolbutton",
        background=CARD_ALT,
        foreground=TEXT_MUTED,
        bordercolor=BORDER,
        focusthickness=0,
        focuscolor=CARD_ALT,
        relief="flat",
        padding=(10, 7),
        anchor="center",
    )
    style.map(
        "Seg.Toolbutton",
        background=[("selected", ACCENT), ("active", "#E9EAF2"), ("pressed", "#E2E3EE")],
        foreground=[("selected", "#FFFFFF"), ("active", TEXT)],
        bordercolor=[("selected", ACCENT)],
    )

    style.configure("Card.TCheckbutton", background=CARD, foreground=TEXT, focusthickness=0,
                    focuscolor=CARD, padding=(0, 3), indicatorcolor=ACCENT,
                    indicatormargin=(0, 0, 8, 0))
    style.map(
        "Card.TCheckbutton",
        background=[("active", CARD)],
        indicatorcolor=[("selected", ACCENT), ("!selected", "#C7CBD8")],
        foreground=[("disabled", TEXT_FAINT)],
    )
    style.configure("Card.TRadiobutton", background=CARD, foreground=TEXT, focusthickness=0,
                    focuscolor=CARD)
    style.map("Card.TRadiobutton", background=[("active", CARD)])

    style.configure(
        "Accent.Horizontal.TScale",
        background=CARD,
        troughcolor="#EDEEF4",
        bordercolor=CARD,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        focuscolor=CARD,
    )
    style.configure(
        "Modern.Horizontal.TProgressbar",
        background=ACCENT,
        troughcolor="#EDEEF4",
        bordercolor="#EDEEF4",
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        thickness=8,
    )
    style.configure("Card.TEntry", fieldbackground=CARD_ALT, bordercolor=BORDER_STRONG,
                    foreground=TEXT, insertcolor=TEXT, padding=4)
    style.map("Card.TEntry", bordercolor=[("focus", ACCENT)])

    return {
        "family": family,
        "base": base,
        "small": small,
        "title": title,
        "app": app,
        "size_base": size_base,
        "size_small": size_small,
        "size_title": size_title,
        "size_app": size_app,
        "lang": "en" if english else "zh",
        "ui_scale": scale,
    }


def enable_hidpi(root) -> None:
    """Windows 高分屏：开启 DPI 感知并设置 Tk 缩放。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
    try:
        root.tk.call("tk", "scaling", root.winfo_fpixels("1i") / 72.0)
    except Exception:
        pass


# --------------------------------------------------------------------------- #
#  应用图标
# --------------------------------------------------------------------------- #
def app_icon_image(size: int = 256) -> Image.Image:
    """画一枚应用图标：紫色圆角方块 + 左右镜像的图形 + 中轴虚线。"""
    scale = size / 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    radius = int(56 * scale)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=ACCENT)
    # 淡淡的顶部高光
    draw.rounded_rectangle(
        [0, 0, size - 1, int(size * 0.55)], radius=radius, fill="#7C6BF0"
    )
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, outline="#5B4BD6", width=max(1, int(2 * scale)))

    # 左侧的“原图”形状：一个三角形 + 圆点
    cx = size / 2
    tri = [
        (int(cx - 78 * scale), int(size - 58 * scale)),
        (int(cx - 78 * scale), int(74 * scale)),
        (int(cx - 18 * scale), int(size - 58 * scale)),
    ]
    draw.polygon(tri, fill="#FFFFFF")
    draw.ellipse(
        [
            int(cx - 62 * scale),
            int(96 * scale),
            int(cx - 34 * scale),
            int(124 * scale),
        ],
        fill="#FFD166",
    )
    # 镜像（右侧）
    mirrored = img.crop((0, 0, int(cx), size)).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    img.paste(mirrored, (int(cx), 0))
    # 中轴虚线
    dash, gap = int(10 * scale), int(8 * scale)
    y = int(40 * scale)
    while y < size - 40 * scale:
        draw.line(
            [(cx, y), (cx, min(y + dash, size - 40 * scale))],
            fill="#FFFFFF",
            width=max(2, int(4 * scale)),
        )
        y += dash + gap
    return img


def icon_path() -> Path | None:
    """把图标写到用户目录并返回 .ico 路径（失败返回 None）。"""
    try:
        from .config import config_dir

        target = config_dir() / "app.ico"
        if not target.exists() or target.stat().st_size < 1000:
            img = app_icon_image(256)
            img.save(target, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        return target
    except Exception:
        return None


def apply_window_icon(window) -> None:
    path = icon_path()
    if not path:
        return
    try:
        window.iconbitmap(default=str(path))
    except Exception:
        try:
            photo = tk.PhotoImage(file=str(path))
            window.iconphoto(True, photo)
            window._icon_ref = photo  # 防止被回收
        except Exception:
            pass
