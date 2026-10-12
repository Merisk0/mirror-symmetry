# -*- coding: utf-8 -*-
"""现代化 Tkinter 界面。

界面层只做三件事：拿参数、显示预览、调用 core 里已经验证过的图像引擎。
"""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageGrab, ImageTk

from . import core, i18n, theme
from . import mark as mk
from .config import config_dir, load_settings, save_settings

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    HAS_DND = True
except Exception:
    HAS_DND = False

APP_TITLE = "对称表情包生成器"
APP_SUB = "Mirror Symmetry Studio"
VERSION = "v2.3.1"


class ToggleSwitch(tk.Canvas):
    """现代拨动开关（比默认勾选框顺眼）。"""

    default_size = (52, 30)

    def __init__(self, master, variable, command=None, width=None, height=None, bg=theme.CARD):
        if width is None or height is None:
            width, height = self.default_size
        super().__init__(master, width=width, height=height, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.var = variable
        self.command = command
        self.sw, self.sh = width, height
        self.bind("<Button-1>", self._on_click)
        self.bind("<Destroy>", self._on_destroy)
        self._trace = None
        try:
            self._trace = self.var.trace_add("write", lambda *_: self._draw())
        except Exception:
            self._trace = None
        self._draw()

    def _on_destroy(self, _event=None):
        """控件销毁时摘掉变量回调，避免重建界面后回调打到已销毁的控件上。"""
        if self._trace is not None:
            try:
                self.var.trace_remove("write", self._trace)
            except Exception:
                pass
            self._trace = None

    def _on_click(self, _event=None):
        self.var.set(not bool(self.var.get()))
        if self.command is not None:
            self.command()

    def _draw(self):
        try:
            if not self.winfo_exists():
                return
            self.delete("all")
        except Exception:
            return
        try:
            on = bool(self.var.get())
        except Exception:
            return
        track = theme.ACCENT if on else "#D3D6E0"
        r = self.sh / 2
        self.create_oval(0, 0, self.sh, self.sh, fill=track, outline=track)
        self.create_oval(self.sw - self.sh, 0, self.sw, self.sh, fill=track, outline=track)
        self.create_rectangle(r, 0, self.sw - r, self.sh, fill=track, outline=track)
        pad = 3
        size = self.sh - pad * 2
        x0 = self.sw - self.sh + pad if on else pad
        self.create_oval(x0, pad, x0 + size, pad + size, fill="#FFFFFF", outline="")


class SymmetryApp:
    """主窗口。"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = load_settings()
        self.lang = str(self.settings.get("lang", "zh"))
        if self.lang not in i18n.LANGS:
            self.lang = "zh"
        self.lang_var = tk.StringVar(value=self.lang)
        try:
            self.ui_scale = max(0.75, min(2.0, float(self.settings.get("ui_scale", 1.0))))
        except Exception:
            self.ui_scale = 1.0
        self.scale_ui_var = tk.IntVar(value=int(round(self.ui_scale * 100)))
        self.fonts = theme.apply_theme(root, self.lang, self.ui_scale)

        self.src_path: Path | None = None
        self.src_frames: list = []
        self.result_frames: list = []
        self.durations: list = []
        self.gif_loop = 0
        self.frame_index = 0
        self.src_img: Image.Image | None = None
        self.result_img: Image.Image | None = None

        self._photos: dict = {}
        self._checkers: dict = {}
        self._update_job = None
        self._full_job = None
        self._anim_job = None
        self._last_dir = self.settings.get("last_dir") or str(Path.home() / "Pictures")

        self.mode_var = tk.StringVar(value=self.settings.get("mode", "lr_left"))
        self.split_var = tk.DoubleVar(value=float(self.settings.get("split", 50.0)))
        self.split_text = tk.StringVar(value="50%")
        self.scale_var = tk.StringVar(value=str(self.settings.get("scale", "100")))
        self.square_var = tk.BooleanVar(value=bool(self.settings.get("square", False)))
        self.center_var = tk.BooleanVar(value=bool(self.settings.get("center_axis", True)))
        self.custom_size_var = tk.BooleanVar(value=bool(self.settings.get("custom_size", False)))
        self.out_w_var = tk.StringVar(value=str(self.settings.get("out_w", "") or ""))
        self.out_h_var = tk.StringVar(value=str(self.settings.get("out_h", "") or ""))
        self.auto_size_var = tk.StringVar(value="—")
        self.play_var = tk.BooleanVar(value=bool(self.settings.get("play", True)))
        self.frame_var = tk.StringVar(value="当前是静态图")
        self.size_chip = tk.StringVar(value="—")
        self.result_chip = tk.StringVar(value="—")
        self.status_var = tk.StringVar(value="准备就绪")
        self.result_cap_var = tk.StringVar(value="—")
        self.source_cap_var = tk.StringVar(value="—")

        bg = self.settings.get("bg") or [255, 255, 255]
        try:
            self.bg_rgb = tuple(int(v) for v in bg)[:3]
        except Exception:
            self.bg_rgb = (255, 255, 255)

        self._compute_metrics()
        self._build_ui()
        self._bind_keys()
        self._localize()
        self._on_size_toggle(quiet=True)
        self._sync_mode()
        self._on_split()
        self._restore_geometry()
        self.root.after(60, self._refresh_previews)
        self._set_status(self.tr("ready"))

    # ================================================================ 多语言
    def _compute_metrics(self):
        """按当前语言 / 缩放算出界面尺寸。"""
        size_base = int(self.fonts.get("size_base", 12))
        scale = float(self.ui_scale)
        ToggleSwitch.default_size = (int(round(56 * scale)), int(round(32 * scale)))
        self._side_width = max(300, int(round(size_base * 28)))
        self._chip_font = (self.fonts["family"], int(self.fonts.get("size_small", 10)))
        self._placeholder_font = (self.fonts["family"], size_base + 1)
        self._canvas_w = int(round(420 * scale))
        self._canvas_h = int(round(380 * scale))
        self._want_w = int(round(1380 * scale))
        self._want_h = int(round(900 * scale))

    def tr(self, key: str, **kwargs) -> str:
        """动态文案。"""
        return i18n.msg(self.lang, key, **kwargs)

    def ts(self, text: str) -> str:
        """静态文案（按中文原文查表）。"""
        return i18n.static_map(self.lang).get(text, text)

    def _localize(self):
        """把界面上的静态文案换成当前语言。"""
        self.root.title(f"{self.tr('app_title')} {VERSION}")
        table = i18n.static_map(self.lang)
        self._translate_tree(self.root, table)

    def _translate_tree(self, widget, table):
        for child in widget.winfo_children():
            if isinstance(child, tk.Menu):
                self._translate_tree(child, table)
                continue
            try:
                text = child.cget("text")
            except Exception:
                text = None
            if isinstance(text, str) and text.strip():
                padded = text != text.strip()
                target = table.get(text.strip())
                if target:
                    try:
                        child.configure(text=f" {target} " if padded else target)
                    except Exception:
                        pass
            self._translate_tree(child, table)

    def set_language(self, lang: str):
        if lang not in i18n.LANGS or lang == self.lang:
            return
        self.lang = lang
        self.fonts = theme.apply_theme(self.root, lang, self.ui_scale)
        self._rebuild_ui()
        self._set_status(self.tr("ready"))

    def set_ui_scale(self, value: float):
        """菜单里的界面缩放（0.75 ~ 2.0，即 75% ~ 200%）。"""
        try:
            value = max(0.75, min(2.0, float(value)))
        except Exception:
            return
        if abs(value - self.ui_scale) < 1e-6:
            return
        self.ui_scale = value
        self.scale_ui_var.set(int(round(value * 100)))
        self.fonts = theme.apply_theme(self.root, self.lang, self.ui_scale)
        self._rebuild_ui()
        # 放大后窗口太小的话，顺手把窗口也放大一点
        try:
            if self.root.winfo_height() < self._want_h * 0.8:
                self.root.geometry(f"{self._want_w}x{self._want_h}")
                self.root.after(120, self._clamp_to_screen)
        except Exception:
            pass
        self._set_status(self.tr("ready"))

    def _rebuild_ui(self):
        """切换语言后重建界面（保留已载入的图片与所有设置）。"""
        self._stop_animation()
        for child in self.root.winfo_children():
            child.destroy()
        self._photos.clear()
        self._checkers.clear()
        self._compute_metrics()
        self._build_ui()
        self._bind_keys()
        self._localize()
        self._on_size_toggle(quiet=True)
        self._sync_mode()
        self._on_split()
        self.root.after(60, self._refresh_previews)
        self._refresh_previews()
        self._update_captions()

    # ==================================================================== 布局
    def _build_ui(self):
        self.root.title(f"{APP_TITLE} {VERSION}")
        self.root.minsize(880, 560)
        self.root.configure(bg=theme.BG)

        self._build_appbar()

        body = ttk.Frame(self.root, padding=(18, 14, 18, 6))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_sidebar(body)
        self._build_preview(body)
        self._build_statusbar()

    def _build_appbar(self):
        bar = tk.Frame(self.root, bg=theme.CARD, height=76)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=theme.CARD)
        left.pack(side="left", padx=(18, 0), pady=13)
        self._icon_photo = self._make_icon_photo(30)
        if self._icon_photo is not None:
            tk.Label(left, image=self._icon_photo, bg=theme.CARD).pack(side="left", padx=(0, 10))
        titles = tk.Frame(left, bg=theme.CARD)
        titles.pack(side="left")
        ttk.Label(titles, text=APP_TITLE, style="BarTitle.TLabel").pack(anchor="w")
        subtitle = APP_SUB if self.lang == "zh" else "Image & GIF mirror studio"
        ttk.Label(titles, text=f"{subtitle} · {VERSION}", style="BarSub.TLabel").pack(anchor="w")

        right = tk.Frame(bar, bg=theme.CARD)
        right.pack(side="right", padx=(0, 18), pady=13)
        ttk.Button(right, text="⋯", width=3, style="Ghost.TButton",
                   command=self._show_menu).pack(side="right", padx=(10, 0))
        ttk.Button(right, text="保存结果", style="Primary.TButton",
                   command=self.save_quick).pack(side="right", padx=(10, 0))
        ttk.Button(right, text="另存为…", style="Ghost.TButton",
                   command=self.save_as).pack(side="right", padx=(10, 0))
        ttk.Separator(right, orient="vertical").pack(side="right", fill="y", padx=10)
        ttk.Button(right, text="批量处理", style="Ghost.TButton",
                   command=self.batch_folder).pack(side="right", padx=(10, 0))
        ttk.Button(right, text="粘贴", style="Ghost.TButton",
                   command=self.paste_image).pack(side="right", padx=(10, 0))
        ttk.Button(right, text="打开图片", style="Ghost.TButton",
                   command=self.open_dialog).pack(side="right")

        tk.Frame(self.root, bg=theme.BORDER, height=1).pack(fill="x")

    def _make_icon_photo(self, size: int):
        try:
            from PIL import ImageTk as _ImageTk

            return _ImageTk.PhotoImage(theme.app_icon_image(size))
        except Exception:
            return None

    def _on_side_scroll(self, first, last):
        """内容超出才显示滚动条。"""
        try:
            if float(first) <= 0.0 and float(last) >= 1.0:
                self.side_scroll.pack_forget()
            else:
                self.side_scroll.pack(side="right", fill="y")
            self.side_scroll.set(first, last)
        except Exception:
            pass

    def _bind_side_wheel(self, active: bool):
        try:
            if active:
                self.root.bind_all("<MouseWheel>", self._side_wheel)
            else:
                self.root.unbind_all("<MouseWheel>")
        except Exception:
            pass

    def _side_wheel(self, event):
        try:
            self.side_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        except Exception:
            pass

    def _card(self, parent, title: str, subtitle: str = ""):
        """一个带标题的白色卡片，返回 (卡片, 内容容器)。"""
        outer = tk.Frame(parent, bg=theme.CARD, highlightthickness=1,
                         highlightbackground=theme.BORDER, bd=0)
        pad = tk.Frame(outer, bg=theme.CARD)
        pad.pack(fill="both", expand=True, padx=14, pady=12)
        head = tk.Frame(pad, bg=theme.CARD)
        head.pack(fill="x")
        ttk.Label(head, text=title, style="Section.TLabel").pack(side="left")
        body = tk.Frame(pad, bg=theme.CARD)
        body.pack(fill="both", expand=True, pady=(8, 0))
        if subtitle:
            ttk.Label(pad, text=subtitle, style="Hint.TLabel").pack(anchor="w", pady=(2, 0))
        return outer, body

    def _build_sidebar(self, parent):
        # 侧栏做成可滚动容器：小屏幕上也能看全所有设置
        wrap = tk.Frame(parent, bg=theme.BG)
        wrap.grid(row=0, column=0, sticky="nsw", padx=(0, 14))
        self.side_canvas = tk.Canvas(wrap, bg=theme.BG, highlightthickness=0, bd=0,
                                     width=self._side_width, height=520)
        self.side_canvas.pack(side="left", fill="y", expand=True)
        side = tk.Frame(self.side_canvas, bg=theme.BG)
        self._side_window = self.side_canvas.create_window((0, 0), window=side, anchor="nw")
        self.side_scroll = ttk.Scrollbar(wrap, orient="vertical", command=self.side_canvas.yview)
        self.side_canvas.configure(yscrollcommand=self._on_side_scroll)
        side.bind("<Configure>", lambda e: self.side_canvas.configure(
            scrollregion=self.side_canvas.bbox("all")))
        self.side_canvas.bind("<Configure>", lambda e: self.side_canvas.itemconfigure(
            self._side_window, width=e.width))
        wrap.bind("<Enter>", lambda e: self._bind_side_wheel(True))
        wrap.bind("<Leave>", lambda e: self._bind_side_wheel(False))

        # ---- 对称方式 ----
        card, body = self._card(side, "对称方式")
        card.pack(fill="x")
        for i, (key, _group, _label) in enumerate(core.MODES):
            ttk.Radiobutton(
                body, text=core.MODE_RADIO[key], value=key, variable=self.mode_var,
                style="Seg.Toolbutton", takefocus=False, command=self._on_mode_change,
            ).grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else 6, 0),
                   pady=(0 if i < 2 else 6, 0))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # ---- 对称轴 ----
        card, body = self._card(side, "对称轴位置")
        card.pack(fill="x", pady=(10, 0))
        self.split_scale = ttk.Scale(
            body, from_=10, to=90, orient="horizontal", variable=self.split_var,
            style="Accent.Horizontal.TScale", command=self._on_split,
        )
        self.split_scale.pack(fill="x")
        row = tk.Frame(body, bg=theme.CARD)
        row.pack(fill="x", pady=(6, 0))
        ttk.Label(row, textvariable=self.split_text, style="Chip.TLabel").pack(side="left")
        ttk.Button(row, text="回到正中", style="Ghost.TButton",
                   command=self._center_split).pack(side="right")
        ttk.Label(body, text="偏离正中时，图案会平铺成万花筒效果。",
                  style="Hint.TLabel", wraplength=250, justify="left").pack(anchor="w", pady=(8, 0))

        # ---- 动图 ----
        card, body = self._card(side, "动图")
        card.pack(fill="x", pady=(10, 0))
        row = tk.Frame(body, bg=theme.CARD)
        row.pack(fill="x")
        ToggleSwitch(row, self.play_var, command=self._toggle_play).pack(side="left")
        ttk.Label(row, text="播放动画预览", style="Card.TLabel").pack(side="left", padx=(10, 0))
        ttk.Label(row, text="空格", style="Chip.TLabel").pack(side="right")
        ttk.Label(body, textvariable=self.frame_var, style="Hint.TLabel",
                  wraplength=250, justify="left").pack(anchor="w", pady=(4, 0))

        # ---- 导出 ----
        card, body = self._card(side, "导出设置")
        card.pack(fill="x", pady=(10, 0))
        row = tk.Frame(body, bg=theme.CARD)
        row.pack(fill="x")
        ttk.Label(row, text="倍率", style="Card.TLabel").pack(side="left")
        entry = ttk.Entry(row, textvariable=self.scale_var, width=6, justify="right",
                          style="Card.TEntry")
        entry.pack(side="left", padx=(8, 4))
        ttk.Label(row, text="%", style="CardMuted.TLabel").pack(side="left")
        entry.bind("<Return>", lambda e: self._update())
        entry.bind("<FocusOut>", lambda e: self._update())

        row = tk.Frame(body, bg=theme.CARD)
        row.pack(fill="x", pady=(8, 0))
        ToggleSwitch(row, self.center_var, command=self._update).pack(side="left")
        ttk.Label(row, text="对称轴居中输出", style="Card.TLabel").pack(side="left", padx=(10, 0))
        ttk.Label(body, text="偏心时自动裁成对称尺寸，让对称轴落在正中间。",
                  style="Hint.TLabel", wraplength=250, justify="left").pack(anchor="w", pady=(4, 0))

        row = tk.Frame(body, bg=theme.CARD)
        row.pack(fill="x", pady=(8, 0))
        ToggleSwitch(row, self.custom_size_var, command=self._on_size_toggle).pack(side="left")
        ttk.Label(row, text="输出尺寸", style="Card.TLabel").pack(side="left", padx=(10, 0))

        row = tk.Frame(body, bg=theme.CARD)
        row.pack(fill="x", pady=(4, 0))
        ttk.Label(row, textvariable=self.auto_size_var, style="Chip.TLabel").pack(side="left")

        row = tk.Frame(body, bg=theme.CARD)
        row.pack(fill="x", pady=(6, 0))
        ttk.Label(row, text="自定义", style="Hint.TLabel").pack(side="left")
        self.out_w_entry = ttk.Entry(row, textvariable=self.out_w_var, width=6,
                                     justify="right", style="Card.TEntry")
        self.out_w_entry.pack(side="left", padx=(8, 2))
        ttk.Label(row, text="×", style="CardMuted.TLabel").pack(side="left")
        self.out_h_entry = ttk.Entry(row, textvariable=self.out_h_var, width=6,
                                     justify="right", style="Card.TEntry")
        self.out_h_entry.pack(side="left", padx=(2, 0))
        for ent in (self.out_w_entry, self.out_h_entry):
            ent.bind("<Return>", lambda e: self._update())
            ent.bind("<FocusOut>", lambda e: self._update())

        row = tk.Frame(body, bg=theme.CARD)
        row.pack(fill="x", pady=(8, 0))
        ToggleSwitch(row, self.square_var, command=self._update).pack(side="left")
        ttk.Label(row, text="补成正方形（透明边）", style="Card.TLabel").pack(side="left", padx=(10, 0))

        row = tk.Frame(body, bg=theme.CARD)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="JPG/BMP 底色", style="Card.TLabel").pack(side="left")
        self.swatch = tk.Frame(row, bg="#%02x%02x%02x" % self.bg_rgb, width=22, height=22,
                               highlightthickness=1, highlightbackground=theme.BORDER_STRONG,
                               cursor="hand2")
        self.swatch.pack(side="left", padx=(10, 6))
        self.swatch.pack_propagate(False)
        self.swatch.bind("<Button-1>", lambda e: self.pick_bg_color())
        ttk.Button(row, text="选择", style="Ghost.TButton",
                   command=self.pick_bg_color).pack(side="left")

        ttk.Label(body, text="动图存 GIF / WebP 保留动画，存 PNG/JPG 只存当前帧。",
                  style="Hint.TLabel", wraplength=250, justify="left").pack(anchor="w", pady=(8, 0))


    def _build_preview(self, parent):
        area = ttk.Frame(parent)
        area.grid(row=0, column=1, sticky="nsew")
        area.columnconfigure(0, weight=1)
        area.columnconfigure(1, weight=1)
        area.rowconfigure(0, weight=1)

        self.src_canvas, self.src_chip, self.src_cap = self._preview_card(
            area, "原图", self.size_chip, self.source_cap_var
        )
        self.src_canvas.master.master.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

        self.res_canvas, self.res_chip, self.res_cap = self._preview_card(
            area, "对称结果", self.result_chip, self.result_cap_var
        )
        self.res_canvas.master.master.grid(row=0, column=1, sticky="nsew", padx=(7, 0))

    def _preview_card(self, parent, title, chip_var, cap_var):
        outer = tk.Frame(parent, bg=theme.CARD, highlightthickness=1,
                         highlightbackground=theme.BORDER, bd=0)
        inner = tk.Frame(outer, bg=theme.CARD)
        inner.pack(fill="both", expand=True, padx=14, pady=12)

        head = tk.Frame(inner, bg=theme.CARD)
        head.pack(fill="x")
        ttk.Label(head, text=title, style="Section.TLabel").pack(side="left")
        ttk.Label(head, textvariable=chip_var, style="Chip.TLabel").pack(side="right")

        canvas = tk.Canvas(inner, bg=theme.CANVAS_BG, highlightthickness=1,
                           highlightbackground=theme.BORDER, bd=0,
                           width=self._canvas_w, height=self._canvas_h)
        canvas.pack(fill="both", expand=True, pady=(10, 8))
        cap = ttk.Label(inner, textvariable=cap_var, style="CardMuted.TLabel", anchor="center")
        cap.pack(fill="x")
        canvas.bind("<Configure>", lambda e: self._refresh_previews())
        return canvas, None, cap

    def _build_statusbar(self):
        tk.Frame(self.root, bg=theme.BORDER, height=1).pack(fill="x")
        bar = tk.Frame(self.root, bg=theme.BG,
                       height=32 + int(self.fonts.get("size_small", 9)))
        bar.pack(fill="x")
        bar.pack_propagate(False)
        self.status_dot = tk.Canvas(bar, width=10, height=10, bg=theme.BG, highlightthickness=0)
        self.status_dot.pack(side="left", padx=(18, 8), pady=10)
        self.status_dot.create_oval(1, 1, 9, 9, fill=theme.SUCCESS, outline="")
        ttk.Label(bar, textvariable=self.status_var, style="Status.TLabel").pack(
            side="left", pady=6
        )
        ttk.Label(bar, text="支持 PNG · JPG · WebP · GIF(动图) · BMP", style="Status.TLabel").pack(
            side="right", padx=(0, 18), pady=6
        )

    # ================================================================ 交互事件
    def _bind_keys(self):
        bind = self.root.bind
        bind("<Control-o>", lambda e: (self.open_dialog(), "break")[1])
        bind("<Control-O>", lambda e: (self.open_dialog(), "break")[1])
        bind("<Control-v>", lambda e: (self.paste_image(), "break")[1])
        bind("<Control-V>", lambda e: (self.paste_image(), "break")[1])
        bind("<Control-s>", lambda e: (self.save_quick(), "break")[1])
        bind("<Control-S>", lambda e: (self.save_as(), "break")[1])
        bind("<Control-r>", lambda e: (self.clear_all(), "break")[1])
        bind("<Control-R>", lambda e: (self.clear_all(), "break")[1])
        bind("<Left>", lambda e: self._arrow(-1))
        bind("<Right>", lambda e: self._arrow(1))
        bind("<Up>", lambda e: self._arrow(-1))
        bind("<Down>", lambda e: self._arrow(1))
        bind("<space>", lambda e: self._space_key())
        bind("<F1>", lambda e: (self.show_about(), "break")[1])
        bind("<Control-Alt-m>", lambda e: (self.read_mark_dialog(), "break")[1])
        bind("<Escape>", lambda e: self._stop_animation())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        if HAS_DND:
            try:
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind("<<Drop>>", self._on_drop)
            except Exception:
                pass

    def _on_drop(self, event):
        try:
            items = self.root.tk.splitlist(event.data)
        except Exception:
            items = [event.data]
        if items:
            self.load_path(items[0])

    def _field_has_focus(self) -> bool:
        try:
            widget = self.root.focus_get()
        except Exception:
            widget = None
        return isinstance(widget, (tk.Entry, tk.Text))

    def _arrow(self, step: int):
        if self._field_has_focus():
            return
        self._cycle_mode(step)

    def _space_key(self):
        if self._field_has_focus():
            return
        if len(self.src_frames) < 2:
            return
        self.play_var.set(not self.play_var.get())
        self._toggle_play()
        return "break"

    def _toggle_play(self):
        if self.play_var.get():
            self._restart_animation()
        else:
            self._stop_animation()

    def _cycle_mode(self, step: int):
        keys = [key for key, _g, _l in core.MODES]
        idx = keys.index(self.mode_var.get()) if self.mode_var.get() in keys else 0
        self.mode_var.set(keys[(idx + step) % len(keys)])
        self._on_mode_change()

    def _on_mode_change(self):
        self._sync_mode()
        self._on_split()

    def _on_split(self, _value=None):
        value = float(self.split_var.get())
        if abs(value - 50) < 0.6:
            self.split_text.set(self.tr("axis_centre"))
        else:
            self.split_text.set(self.tr("axis_custom", v=value))
        self._schedule_update()

    def _center_split(self):
        self.split_var.set(50.0)
        try:
            self.split_scale.set(50.0)
        except Exception:
            pass
        self._on_split()

    def _sync_mode(self):
        state = "normal" if self.mode_var.get() in core.CUT_MODES else "disabled"
        try:
            self.split_scale.configure(state=state)
        except Exception:
            pass

    def _schedule_update(self):
        if self._update_job is not None:
            try:
                self.root.after_cancel(self._update_job)
            except Exception:
                pass
        self._update_job = self.root.after(40, self._update)

    # ================================================================ 动画播放
    def _restart_animation(self):
        self._stop_animation()
        if len(self.src_frames) < 2 or not self.play_var.get():
            return
        self._anim_job = self.root.after(self._current_duration(), self._anim_tick)

    def _stop_animation(self):
        if self._anim_job is not None:
            try:
                self.root.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None

    def _current_duration(self) -> int:
        if not self.durations:
            return core.DEFAULT_DURATION
        idx = min(max(self.frame_index, 0), len(self.durations) - 1)
        return max(20, int(self.durations[idx] or core.DEFAULT_DURATION))

    def _anim_tick(self):
        self._anim_job = None
        count = len(self.src_frames)
        if count < 2 or not self.play_var.get():
            return
        self.frame_index = (self.frame_index + 1) % count
        self.src_img = self.src_frames[self.frame_index]
        self.result_img = (
            self.result_frames[self.frame_index] if len(self.result_frames) == count else None
        )
        self._refresh_previews()
        self._update_captions()
        self._restart_animation()

    # ================================================================ 文件操作
    def open_dialog(self):
        path = filedialog.askopenfilename(
            title=self.tr("open_title"),
            initialdir=self._last_dir,
            filetypes=[
                (self.ts("图片 / 动图"), "*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tif *.tiff"),
                (self.ts("GIF 动图"), "*.gif"),
                (self.ts("所有文件"), "*.*"),
            ],
        )
        if path:
            self.load_path(path)

    def load_path(self, path):
        try:
            frames, durations, loop = core.load_frames(path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, self.tr("opened_failed", path=path, err=exc))
            return
        self.src_path = Path(path)
        self._last_dir = str(self.src_path.parent)
        self._set_frames(frames, durations, loop)
        self._update()
        w, h = frames[0].size
        if len(frames) > 1:
            self._set_status(self.tr("loaded_anim", name=self.src_path.name, w=w, h=h,
                                     n=len(frames)))
        else:
            self._set_status(self.tr("loaded", name=self.src_path.name, w=w, h=h))

    def paste_image(self):
        try:
            data = ImageGrab.grabclipboard()
        except Exception:
            data = None
        if data is None:
            self._set_status(self.tr("clip_empty"))
            return
        if isinstance(data, list):
            candidates = [p for p in data if str(p).lower().endswith(core.IMAGE_EXTS)]
            if not candidates:
                self._set_status(self.tr("clip_no_file"))
                return
            self.load_path(candidates[0])
            return
        img = data.convert("RGBA")
        self.src_path = None
        self._set_frames([img], [core.DEFAULT_DURATION], 0)
        self._update()
        self._set_status(self.tr("pasted", w=img.width, h=img.height))

    def clear_all(self):
        self._stop_animation()
        self.src_path = None
        self._set_frames([], [], 0)
        self._update()
        self._set_status(self.tr("cleared"))

    def _set_frames(self, frames, durations, loop):
        self.src_frames = list(frames)
        self.durations = list(durations)
        self.gif_loop = int(loop or 0)
        self.result_frames = []
        self.frame_index = 0
        self.src_img = self.src_frames[0] if self.src_frames else None
        self.result_img = None
        if len(self.src_frames) < 2:
            self.play_var.set(True)

    # ==================================================================== 导出
    def _is_animated(self) -> bool:
        return len(self.src_frames) > 1

    def _scale_factor(self) -> float:
        raw = str(self.scale_var.get()).strip().replace("％", "").replace("%", "")
        try:
            value = float(raw)
        except ValueError:
            value = 100.0
        value = min(max(value, 5.0), 800.0)
        return value / 100.0

    def _target_size(self):
        """自定义输出尺寸 (w, h)，未启用或非法时返回 None。"""
        if not self.custom_size_var.get():
            return None
        try:
            w = int(float(str(self.out_w_var.get()).strip()))
            h = int(float(str(self.out_h_var.get()).strip()))
        except Exception:
            return None
        if w < 1 or h < 1:
            return None
        return (min(w, 8000), min(h, 8000))

    def _mark_payload(self, frames, durations=None):
        """每次导出都会写入固定标记（不可配置、界面上不显示）。"""
        if not frames:
            return None
        try:
            return mk.make_payload(frames, durations)
        except Exception:
            return None

    def read_mark_dialog(self):
        """隐藏入口（Ctrl+Alt+M）：读回导出文件里的标记。"""
        path = filedialog.askopenfilename(
            title=self.tr("mk_pick"),
            initialdir=self._last_dir,
            filetypes=[
                (self.ts("图片 / 动图"), "*.png *.jpg *.jpeg *.bmp *.webp *.gif *.tif *.tiff"),
                (self.ts("所有文件"), "*.*"),
            ],
        )
        if not path:
            return
        try:
            info = mk.read_mark(path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, self.tr("mk_fail", err=exc))
            return
        if not info:
            messagebox.showinfo(APP_TITLE, self.tr("mk_none"))
            return
        method = self.tr("mk_method_lsb") if info.get("method") == "lsb" \
            else self.tr("mk_method_meta")
        messagebox.showinfo(
            APP_TITLE,
            self.tr("mk_found", tag=info.get("text") or "—", time=info.get("time", "—"),
                    size=info.get("size", "—"), sig=info.get("signature", "—"),
                    method=method),
        )

    def _on_size_toggle(self, quiet: bool = False):
        state = "normal" if self.custom_size_var.get() else "disabled"
        for name in ("out_w_entry", "out_h_entry"):
            ent = getattr(self, name, None)
            if ent is not None:
                try:
                    ent.configure(state=state)
                except Exception:
                    pass
        if not quiet:
            self._update()

    def _auto_size(self):
        """按倍率 / 正方形算出的自动输出尺寸。"""
        if not self.result_img:
            return (0, 0)
        w = max(1, int(round(self.result_img.width * self._scale_factor())))
        h = max(1, int(round(self.result_img.height * self._scale_factor())))
        if self.square_var.get():
            side = max(w, h)
            w = h = side
        return (w, h)

    def _resize_like(self, img: Image.Image) -> Image.Image:
        size = self._target_size()
        if size:
            img = img.resize(size, core.RESAMPLE)
            if self.square_var.get():
                img = core.fit_square(img)
            return img
        return core.resize_image(img, self._scale_factor(), self.square_var.get())

    def _prepare_frames(self, animated: bool = True) -> list:
        if not self.result_frames:
            return []
        if animated and len(self.result_frames) > 1:
            return [self._resize_like(f) for f in self.result_frames]
        idx = min(max(self.frame_index, 0), len(self.result_frames) - 1)
        return [self._resize_like(self.result_frames[idx])]

    def _export_size(self):
        if not self.result_img:
            return None
        size = self._target_size()
        if size:
            if self.square_var.get():
                side = max(size)
                return (side, side)
            return size
        return self._auto_size()

    def _save_frames(self, path: str, frames: list, durations=None, loop: int = 0) -> None:
        payload = self._mark_payload(frames, durations)
        ext = Path(path).suffix.lower()
        if ext == ".gif":
            core.save_gif(path, frames, durations, loop, mark=payload)
        elif ext == ".webp":
            core.save_webp(path, frames, durations, loop, lossless=len(frames) > 1,
                           mark=payload)
        elif ext in (".jpg", ".jpeg"):
            img = core.flatten_to_rgb(frames[0], self.bg_rgb)
            meta = mk.metadata_for("JPEG", payload) if payload else {}
            img.save(path, "JPEG", quality=95, subsampling=0, **meta)
        elif ext == ".bmp":
            img = core.flatten_to_rgb(frames[0], self.bg_rgb)
            if payload:
                try:
                    img = mk.embed_lsb(img, payload)
                except ValueError:
                    pass
            img.save(path, "BMP")
        else:
            img = frames[0]
            if payload:
                try:
                    img = mk.embed_lsb(img, payload)
                except ValueError:
                    pass
            meta = mk.metadata_for("PNG", payload) if payload else {}
            img.save(path, "PNG", **meta)

    def _save_image(self, path: str) -> str:
        ext = Path(path).suffix.lower()
        animated_out = len(self.result_frames) > 1 and ext in (".gif", ".webp")
        frames = self._prepare_frames(animated=animated_out)
        if not frames:
            raise RuntimeError("还没有结果可以保存")
        self._save_frames(path, frames, self.durations, self.gif_loop)
        name = Path(path).name
        if len(self.result_frames) > 1 and not animated_out:
            return self.tr("saved_static", name=name)
        if animated_out:
            return self.tr("saved_anim", name=name, n=len(frames))
        return self.tr("saved", name=name)

    def _need_image(self) -> bool:
        if not self.result_frames:
            messagebox.showinfo(APP_TITLE, self.tr("no_image"))
            return True
        return False

    def _default_output_path(self) -> Path:
        stem = self.src_path.stem if self.src_path else "对称图"
        folder = self.src_path.parent if self.src_path else Path(self._last_dir)
        if not Path(folder).exists():
            folder = Path.home()
        ext = ".gif" if self._is_animated() else ".png"
        out = Path(folder) / f"{stem}_对称_{self.mode_var.get()}{ext}"
        index = 2
        while out.exists():
            out = Path(folder) / f"{stem}_对称_{self.mode_var.get()}_{index}{ext}"
            index += 1
        return out

    def save_quick(self):
        if self._need_image():
            return
        out = self._default_output_path()
        try:
            note = self._save_image(str(out))
        except Exception as exc:
            messagebox.showerror(APP_TITLE, self.tr("save_failed", err=exc))
            return
        self._last_dir = str(out.parent)
        self._set_status(f"{note}　→　{out}")

    def save_as(self):
        if self._need_image():
            return
        default = self._default_output_path()
        filetypes = []
        if self._is_animated():
            filetypes.append((self.ts("动画 GIF（保留动画）"), "*.gif"))
            filetypes.append((self.ts("动画 WebP（动画 + 透明）"), "*.webp"))
        else:
            filetypes.append((self.ts("WebP 图片（支持透明）"), "*.webp"))
        filetypes += [
            (self.ts("PNG 图片（支持透明）"), "*.png"),
            (self.ts("JPEG 图片"), "*.jpg *.jpeg"),
            (self.ts("BMP 图片"), "*.bmp"),
            (self.ts("GIF 图片"), "*.gif"),
        ]
        path = filedialog.asksaveasfilename(
            title=self.tr("save_title"),
            initialdir=str(default.parent),
            initialfile=default.name,
            defaultextension=default.suffix,
            filetypes=filetypes,
        )
        if not path:
            return
        try:
            note = self._save_image(path)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, self.tr("save_failed", err=exc))
            return
        self._last_dir = str(Path(path).parent)
        self._set_status(f"{note}　→　{path}")

    def pick_bg_color(self):
        rgb, _hex = colorchooser.askcolor(color="#%02x%02x%02x" % self.bg_rgb, title="选择底色")
        if rgb:
            self.bg_rgb = tuple(int(v) for v in rgb)
            self.swatch.configure(bg="#%02x%02x%02x" % self.bg_rgb)

    # ================================================================ 批量处理
    def batch_folder(self):
        src_dir = filedialog.askdirectory(title=self.tr("batch_pick"), initialdir=self._last_dir)
        if not src_dir:
            return
        folder = Path(src_dir)
        files = sorted(
            p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in core.IMAGE_EXTS
        )
        if not files:
            messagebox.showinfo(APP_TITLE, self.tr("batch_none"))
            return
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = folder / f"对称输出_{stamp}"
        if not messagebox.askokcancel(
            APP_TITLE,
            self.tr(
                "batch_confirm",
                n=len(files),
                mode=i18n.mode_label(self.lang, self.mode_var.get()),
                axis=self.split_var.get(),
                scale=self._scale_factor() * 100,
                square=(self.tr("batch_square") if self.square_var.get() else ""),
                out=out_dir.name,
            ) + "\n\n" + self.tr("batch_start_q"),
        ):
            return

        progress = self._progress_dialog(self.tr("batch_running"), len(files))
        self._last_dir = str(folder)

        def on_progress(index, total, name):
            if progress is not None:
                progress.update(index, total, name)

        try:
            ok, animated, failed = core.export_frames(
                folder, out_dir, self.mode_var.get(), self.split_var.get() / 100.0,
                self._scale_factor(), self.square_var.get(), on_progress=on_progress,
                center_axis=bool(self.center_var.get()), target_size=self._target_size(),
                mark_text=True,
            )
        finally:
            if progress is not None:
                progress.close()

        msg = self.tr("batch_done", ok=ok, anim=animated, bad=len(failed), out=out_dir)
        if failed:
            msg += self.tr("batch_failed", list="\n".join(failed[:8]))
        self._set_status(self.tr("batch_finished", out=out_dir))
        if messagebox.askyesno(APP_TITLE, msg + self.tr("batch_open_q")):
            self._open_path(out_dir)

    def _progress_dialog(self, title: str, total: int):
        """批量处理时的进度窗口。"""
        top = tk.Toplevel(self.root)
        top.title(title)
        top.configure(bg=theme.CARD)
        top.resizable(False, False)
        top.transient(self.root)
        try:
            top.grab_set()
        except Exception:
            pass
        frame = tk.Frame(top, bg=theme.CARD)
        frame.pack(fill="both", expand=True, padx=22, pady=18)
        label = ttk.Label(frame, text=self.tr("batch_prepare"), style="Card.TLabel")
        label.pack(anchor="w")
        bar = ttk.Progressbar(frame, orient="horizontal", mode="determinate", length=360,
                              maximum=max(1, total), style="Modern.Horizontal.TProgressbar")
        bar.pack(fill="x", pady=(10, 0))
        hint = ttk.Label(frame, text="", style="CardMuted.TLabel")
        hint.pack(anchor="w", pady=(8, 0))
        top.update_idletasks()
        try:
            x = self.root.winfo_rootx() + (self.root.winfo_width() - top.winfo_width()) // 2
            y = self.root.winfo_rooty() + (self.root.winfo_height() - top.winfo_height()) // 3
            top.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        class Progress:
            def update(self, index, count, name):
                try:
                    bar["value"] = index
                    label.configure(text=self.tr("batch_progress", i=index, n=count))
                    hint.configure(text=name[:60])
                    top.update_idletasks()
                    top.update()
                except Exception:
                    pass

            def close(self):
                try:
                    top.grab_release()
                except Exception:
                    pass
                top.destroy()

        return Progress()

    def _open_path(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception:
            pass

    # ================================================================ 预览渲染
    def _update(self):
        self._update_job = None
        count = len(self.src_frames)
        if count == 0:
            self._stop_animation()
            self.result_frames = []
            self.src_img = None
            self.result_img = None
            self._refresh_previews()
            self._update_captions()
            return
        self.frame_index = min(max(self.frame_index, 0), count - 1)
        if count > core.QUICK_FRAME_LIMIT:
            self._compute_frames(only_index=self.frame_index)
            if self._full_job is not None:
                try:
                    self.root.after_cancel(self._full_job)
                except Exception:
                    pass
            self._full_job = self.root.after(320, self._finish_full_update)
        else:
            self._compute_frames()
            self._restart_animation()
        self._refresh_previews()
        self._update_captions()

    def _finish_full_update(self):
        self._full_job = None
        if not self.src_frames:
            return
        self._compute_frames()
        self._refresh_previews()
        self._update_captions()
        self._restart_animation()

    def _compute_frames(self, only_index=None):
        mode = self.mode_var.get()
        split = self.split_var.get() / 100.0
        count = len(self.src_frames)
        center = bool(self.center_var.get())
        if only_index is None or len(self.result_frames) != count:
            self.result_frames = [
                core.make_symmetric(f, mode, split, center) for f in self.src_frames
            ]
        else:
            self.result_frames[only_index] = core.make_symmetric(
                self.src_frames[only_index], mode, split, center
            )
        self.src_img = self.src_frames[self.frame_index]
        self.result_img = self.result_frames[self.frame_index]

    def _axis(self):
        mode = self.mode_var.get()
        frac = self.split_var.get() / 100.0
        if mode in ("lr_left", "lr_right"):
            return ("v", frac)
        if mode in ("tb_top", "tb_bottom"):
            return ("h", frac)
        return None

    def _checker(self, size):
        key = (int(size[0]), int(size[1]))
        img = self._checkers.get(key)
        if img is None:
            if len(self._checkers) > 24:
                self._checkers.clear()
            img = core.checkerboard(key)
            self._checkers[key] = img
        return img

    def _refresh_previews(self):
        if getattr(self, "src_canvas", None) is None or getattr(self, "res_canvas", None) is None:
            return
        axis = self._axis()
        self._draw(self.src_canvas, self.src_img,
                   self.ts("拖入图片 / GIF\n\n或点击右上角「打开图片」"), axis)
        self._draw(self.res_canvas, self.result_img,
                   self.ts("对称结果会显示在这里\n\n动图会逐帧镜像并播放"), axis)

    def _draw(self, canvas: tk.Canvas, img, placeholder: str, axis):
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 20 or height < 20:
            return
        if img is None:
            canvas.create_oval(
                width / 2 - 26, height / 2 - 62, width / 2 + 26, height / 2 - 10,
                outline=theme.BORDER_STRONG, width=2, dash=(4, 3),
            )
            canvas.create_line(
                width / 2, height / 2 - 58, width / 2, height / 2 - 14,
                fill=theme.TEXT_FAINT, dash=(3, 3),
            )
            canvas.create_text(
                width / 2, height / 2 + 14, text=placeholder, fill=theme.TEXT_MUTED,
                font=self._placeholder_font, justify="center",
            )
            return

        pad = 20
        scale = min((width - 2 * pad) / img.width, (height - 2 * pad) / img.height)
        scale = max(0.02, min(scale, 4.0))
        nw = max(1, int(round(img.width * scale)))
        nh = max(1, int(round(img.height * scale)))
        thumb = img.resize((nw, nh), core.RESAMPLE)

        if thumb.mode in ("RGBA", "LA") or (thumb.mode == "P" and "transparency" in thumb.info):
            base = self._checker((nw, nh)).convert("RGBA")
            base.alpha_composite(thumb.convert("RGBA"))
        else:
            base = thumb.convert("RGBA")

        photo = ImageTk.PhotoImage(base)
        x0 = int((width - nw) / 2)
        y0 = int((height - nh) / 2)
        canvas.create_rectangle(x0 - 1, y0 - 1, x0 + nw, y0 + nh, outline=theme.BORDER_STRONG)
        canvas.create_image(x0, y0, image=photo, anchor="nw")
        self._photos[str(canvas)] = photo  # 防止被 GC

        if axis:
            kind, frac = axis
            if kind == "v":
                x = x0 + nw * frac
                canvas.create_line(x, y0 - 6, x, y0 + nh + 6, fill=theme.ACCENT, width=2, dash=(6, 4))
                canvas.create_rectangle(x + 6, y0 - 20, x + 60, y0 - 2,
                                        fill=theme.ACCENT_SOFT, outline="")
                canvas.create_text(x + 33, y0 - 11, text=self.ts("对称轴"), fill=theme.ACCENT,
                                   font=self._chip_font)
            else:
                y = y0 + nh * frac
                canvas.create_line(x0 - 6, y, x0 + nw + 6, y, fill=theme.ACCENT, width=2, dash=(6, 4))
                canvas.create_rectangle(x0 - 6, y + 4, x0 + 48, y + 22,
                                        fill=theme.ACCENT_SOFT, outline="")
                canvas.create_text(x0 + 21, y + 13, text=self.ts("对称轴"), fill=theme.ACCENT,
                                   font=self._chip_font)

    def _update_captions(self):
        label = i18n.mode_label(self.lang, self.mode_var.get())
        count = len(self.src_frames)
        if self.src_img is None:
            self.source_cap_var.set("—")
            self.result_cap_var.set("—")
            self.size_chip.set("—")
            self.result_chip.set("—")
            self.auto_size_var.set("—")
            self.frame_var.set(self.tr("chip_static"))
            return

        name = self.src_path.name if self.src_path else self.tr("paste_label")
        size = f"{self.src_img.width}×{self.src_img.height}"
        if count > 1:
            self.size_chip.set(self.tr("chip_gif", n=count))
            loop_text = (self.tr("loop_forever") if self.gif_loop == 0
                         else str(self.gif_loop))
            self.frame_var.set(self.tr("frame_info", i=self.frame_index + 1, n=count,
                                       ms=self._current_duration(), loop=loop_text))
        else:
            self.size_chip.set(self.tr("chip_static"))
            self.frame_var.set(self.tr("chip_static"))
        self.source_cap_var.set(f"{name} · {size}")

        self.result_chip.set(f"{self.result_img.width}×{self.result_img.height}")
        if self._target_size():
            self.auto_size_var.set(f"{self._target_size()[0]}×{self._target_size()[1]}")
        else:
            auto = self._auto_size()
            self.auto_size_var.set(self.tr("auto_size", w=auto[0], h=auto[1]))

        text = label
        if count > 1:
            text += " · " + self.tr("anim_frames", n=count)
        export_size = self._export_size()
        if export_size and tuple(export_size) != tuple(self.result_img.size):
            text += " · " + self.tr("export_size", w=export_size[0], h=export_size[1])
        self.result_cap_var.set(text)

    def _set_status(self, text: str):
        self.status_var.set(text)

    # ============================================================ 菜单 / 关于
    def _show_menu(self):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=self.ts("关于本软件"), command=self.show_about)
        menu.add_separator()
        lang_menu = tk.Menu(menu, tearoff=0)
        for code in i18n.LANGS:
            lang_menu.add_radiobutton(
                label=i18n.LANG_NAMES[code], value=code, variable=self.lang_var,
                command=lambda c=code: self.set_language(c),
            )
        menu.add_cascade(label=self.ts("语言 / Language"), menu=lang_menu)
        scale_menu = tk.Menu(menu, tearoff=0)
        for pct in (100, 110, 125, 150):
            scale_menu.add_radiobutton(
                label=f"{pct}%", value=pct, variable=self.scale_ui_var,
                command=lambda p=pct: self.set_ui_scale(p / 100.0),
            )
        menu.add_cascade(label=self.ts("界面缩放"), menu=scale_menu)
        menu.add_separator()
        menu.add_command(label=self.ts("打开设置目录"),
                         command=lambda: self._open_path(config_dir()))
        menu.add_command(label=self.ts("清空图片"), command=self.clear_all)
        menu.add_separator()
        menu.add_command(label=self.ts("退出"), command=self.on_close)
        try:
            menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            menu.grab_release()

    def show_about(self):
        top = tk.Toplevel(self.root)
        top.title(self.tr("about_title", app=self.tr("app_title")))
        top.configure(bg=theme.CARD)
        top.resizable(False, False)
        top.transient(self.root)
        frame = tk.Frame(top, bg=theme.CARD)
        frame.pack(fill="both", expand=True, padx=26, pady=22)
        icon = self._make_icon_photo(56)
        if icon is not None:
            label = tk.Label(frame, image=icon, bg=theme.CARD)
            label.image = icon
            label.pack(anchor="w")
        ttk.Label(frame, text=self.tr("app_title"), style="BarTitle.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Label(frame, text=f"{APP_SUB} · {VERSION}", style="BarSub.TLabel").pack(anchor="w")
        ttk.Label(
            frame, text=self.tr("about_body"), style="Hint.TLabel", justify="left",
        ).pack(anchor="w", pady=(12, 0))
        ttk.Button(frame, text=self.ts("好"), style="Primary.TButton", command=top.destroy).pack(
            anchor="e", pady=(16, 0)
        )
        top.update_idletasks()
        try:
            x = self.root.winfo_rootx() + (self.root.winfo_width() - top.winfo_width()) // 2
            y = self.root.winfo_rooty() + (self.root.winfo_height() - top.winfo_height()) // 3
            top.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    # =============================================================== 设置/退出
    def _screen_size(self):
        try:
            return self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        except Exception:
            return 1440, 900

    def _restore_geometry(self):
        geo = str(self.settings.get("geometry") or "")
        if geo:
            try:
                self.root.geometry(geo)
                self.root.after(120, self._clamp_to_screen)
                return
            except Exception:
                pass
        sw, sh = self._screen_size()
        w = max(920, min(getattr(self, "_want_w", 1380), sw - 60))
        h = max(600, min(getattr(self, "_want_h", 900), sh - 110))
        self.root.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 20)}")

    def _clamp_to_screen(self):
        """窗口（含记忆的尺寸）不超出屏幕可视区域。"""
        try:
            sw, sh = self._screen_size()
            w, h = self.root.winfo_width(), self.root.winfo_height()
            x, y = self.root.winfo_x(), self.root.winfo_y()
            nw, nh = min(w, max(880, sw - 20)), min(h, max(560, sh - 40))
            nx = min(max(0, x), max(0, sw - nw - 10))
            ny = min(max(0, y), max(0, sh - nh - 10))
            if (nw, nh, nx, ny) != (w, h, x, y):
                self.root.geometry(f"{nw}x{nh}+{nx}+{ny}")
        except Exception:
            pass

    def on_close(self):
        save_settings(
            {
                "mode": self.mode_var.get(),
                "split": float(self.split_var.get()),
                "scale": str(self.scale_var.get()),
                "square": bool(self.square_var.get()),
                "bg": list(self.bg_rgb),
                "play": bool(self.play_var.get()),
                "geometry": self.root.winfo_geometry(),
                "last_dir": self._last_dir,
                "lang": self.lang,
                "ui_scale": float(self.ui_scale),
                "center_axis": bool(self.center_var.get()),
                "custom_size": bool(self.custom_size_var.get()),
                "out_w": str(self.out_w_var.get()),
                "out_h": str(self.out_h_var.get()),
            }
        )
        self._stop_animation()
        try:
            self.root.destroy()
        except Exception:
            pass


# =============================================================== 自检 / 入口
def run_selftest() -> int:
    """无界面自检：用于验证打包后的 exe 是否完好。"""
    import tempfile

    from PIL import Image

    lines, ok = [], True

    def check(cond, text):
        nonlocal ok
        lines.append(("PASS  " if cond else "FAIL  ") + text)
        if not cond:
            ok = False

    try:
        lines.append(f"version: {VERSION}")
        lines.append(f"frozen: {getattr(sys, 'frozen', False)}")
        lines.append(f"python: {sys.version.split()[0]}")
        import PIL

        lines.append(f"pillow: {PIL.__version__}")

        for size in [(120, 80), (121, 81), (64, 64)]:
            img = Image.new("RGBA", size, (10, 20, 30, 255))
            for mode in [m[0] for m in core.MODES]:
                for split in (0.5, 0.3):
                    out = core.make_symmetric(img, mode, split)
                    check(out.size == size, f"symmetric size {mode} {split} {size}")

        img = Image.new("RGBA", (100, 60), (0, 0, 0, 0))
        for x in range(40):
            for y in range(60):
                img.putpixel((x, y), (255, x * 5 % 256, y * 4 % 256, 255))
        out = core.make_symmetric(img, "lr_left", 0.5)
        px = out.load()
        check(
            all(px[x, y] == px[99 - x, y] for x in range(100) for y in range(0, 60, 7)),
            "pixel-perfect centre mirror",
        )

        tmp = Path(tempfile.mkdtemp(prefix="msselftest_"))
        frames = []
        for i in range(4):
            f = Image.new("RGBA", (60, 40), (0, 0, 0, 0))
            for x in range(6 + i * 6):
                for y in range(40):
                    f.putpixel((x, y), (255, i * 50, 0, 255))
            frames.append(core.make_symmetric(f, "tb_top", 0.5))
        gif = tmp / "t.gif"
        core.save_gif(str(gif), frames, [80, 120, 80, 120], 2)
        back, durs, loop = core.load_frames(gif)
        check(len(back) == 4, f"gif frames roundtrip ({len(back)})")
        check(loop == 2, f"gif loop roundtrip ({loop})")
        check(durs[1] == 120, f"gif duration roundtrip ({durs[1]})")
        webp = tmp / "t.webp"
        core.save_webp(str(webp), frames, [80, 120, 80, 120], 2, lossless=True)
        wb = Image.open(webp)
        check(getattr(wb, "n_frames", 1) == 4, f"webp frames roundtrip ({getattr(wb, 'n_frames', 1)})")
        lines.append(f"temp dir: {tmp}")
    except Exception as exc:  # pragma: no cover
        ok = False
        lines.append(f"EXCEPTION: {exc!r}")

    lines.append("RESULT: " + ("PASS" if ok else "FAIL"))
    report = "\n".join(lines)
    try:
        (Path.cwd() / "selftest_report.txt").write_text(report, encoding="utf-8")
    except Exception:
        pass
    print(report)
    return 0 if ok else 1


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in args:
        return run_selftest()
    if "--version" in args:
        print(f"{APP_TITLE} {VERSION}")
        return 0
    if "--help" in args or "-h" in args:
        print(
            f"{APP_TITLE} {VERSION}\n"
            "用法: mirror-symmetry [图片或GIF]\n"
            "      --selftest  运行自检并写出 selftest_report.txt\n"
            "      --version   显示版本\n"
        )
        return 0

    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    theme.enable_hidpi(root)
    theme.apply_window_icon(root)
    app = SymmetryApp(root)
    files = [a for a in args if not a.startswith("-")]
    if files and Path(files[0]).is_file():
        app.load_path(files[0])
    root.mainloop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


