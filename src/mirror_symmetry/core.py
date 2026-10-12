# -*- coding: utf-8 -*-
"""核心图像引擎：镜像对称、动图读写。

这一层不依赖任何界面代码，可以单独 import、单独测试。
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

try:
    from . import watermark as _wm
except ImportError:  # 直接以脚本方式加载本文件时
    import watermark as _wm

__all__ = [
    "DEFAULT_DURATION",
    "IMAGE_EXTS",
    "make_symmetric",
    "axis_centered_size",
    "load_frames",
    "fit_square",
    "flatten_to_rgb",
    "normalized_durations",
    "save_gif",
    "save_webp",
    "checkerboard",
    "resize_image",
]

DEFAULT_DURATION = 100
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff")

try:  # Pillow 9.1+ / 10+ 写法
    FLIP_LR = Image.Transpose.FLIP_LEFT_RIGHT
    FLIP_TB = Image.Transpose.FLIP_TOP_BOTTOM
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:  # 兼容老版本 Pillow
    FLIP_LR = Image.FLIP_LEFT_RIGHT
    FLIP_TB = Image.FLIP_TOP_BOTTOM
    RESAMPLE = Image.LANCZOS

MODES = [
    ("lr_left", "左右对称", "取左半 -> 镜像到右边"),
    ("lr_right", "左右对称", "取右半 -> 镜像到左边"),
    ("tb_top", "上下对称", "取上半 -> 镜像到下边"),
    ("tb_bottom", "上下对称", "取下半 -> 镜像到上边"),
    ("flip_h", "整图翻转", "整张图片左右翻转"),
    ("flip_v", "整图翻转", "整张图片上下翻转"),
]
MODE_LABEL = {key: label for key, _group, label in MODES}
MODE_RADIO = {
    "lr_left": "左半镜像到右边",
    "lr_right": "右半镜像到左边",
    "tb_top": "上半镜像到下边",
    "tb_bottom": "下半镜像到上边",
    "flip_h": "整图左右翻转",
    "flip_v": "整图上下翻转",
}
CUT_MODES = ("lr_left", "lr_right", "tb_top", "tb_bottom")
# 帧数超过这个值时，拖动对称轴只先算当前帧，停下后再补算全部帧
QUICK_FRAME_LIMIT = 12


def axis_centered_size(w: int, h: int, mode: str, split: float = 0.5):
    """「对称轴居中输出」时的画布尺寸。

    取保留的那半张，镜像后拼成新画布，对称轴正好落在正中间。
    """
    split = min(max(float(split), 0.05), 0.95)
    if abs(split - 0.5) < 1e-9:
        return (w, h)  # 正中时保持原尺寸，本来就已居中
    if mode in ("lr_left", "lr_right"):
        frac = split if mode == "lr_left" else 1.0 - split
        cx = min(max(int(w * frac + 0.5), 1), w - 1)
        return (2 * cx, h)
    if mode in ("tb_top", "tb_bottom"):
        frac = split if mode == "tb_top" else 1.0 - split
        cy = min(max(int(h * frac + 0.5), 1), h - 1)
        return (w, 2 * cy)
    return (w, h)


def make_symmetric(img: Image.Image, mode: str, split: float = 0.5,
                   center_axis: bool = False) -> Image.Image:
    """按 mode 生成对称图。

    split 是 0~1 的对称轴位置，默认 0.5（正中）。
    ``center_axis=False``：输出尺寸与输入相同；轴偏离正中时图案平铺成万花筒。
    ``center_axis=True``：只保留切线一侧的半张图并镜像，输出尺寸随之改变，
    但对称轴永远落在结果的正中间。
    """
    img = img.convert("RGBA")
    w, h = img.size

    if mode == "flip_h":
        return img.transpose(FLIP_LR)
    if mode == "flip_v":
        return img.transpose(FLIP_TB)
    if mode in ("lr_left", "lr_right") and w < 2:
        return img.copy()
    if mode in ("tb_top", "tb_bottom") and h < 2:
        return img.copy()

    split = min(max(float(split), 0.05), 0.95)

    if center_axis and abs(split - 0.5) > 1e-9:
        if mode in ("lr_left", "lr_right"):
            frac = split if mode == "lr_left" else 1.0 - split
            cx = min(max(int(w * frac + 0.5), 1), w - 1)
            if mode == "lr_left":
                half = img.crop((0, 0, cx, h))
            else:
                half = img.crop((w - cx, 0, w, h))
            flip = half.transpose(FLIP_LR)
            out = Image.new("RGBA", (2 * cx, h), (0, 0, 0, 0))
            out.paste(half if mode == "lr_left" else flip, (0, 0))
            out.paste(flip if mode == "lr_left" else half, (cx, 0))
            return out
        frac = split if mode == "tb_top" else 1.0 - split
        cy = min(max(int(h * frac + 0.5), 1), h - 1)
        if mode == "tb_top":
            half = img.crop((0, 0, w, cy))
        else:
            half = img.crop((0, h - cy, w, h))
        flip = half.transpose(FLIP_TB)
        out = Image.new("RGBA", (w, 2 * cy), (0, 0, 0, 0))
        out.paste(half if mode == "tb_top" else flip, (0, 0))
        out.paste(flip if mode == "tb_top" else half, (0, cy))
        return out
    out = img.copy()

    def tile(unit, origin, span, vertical):
        step = unit.height if vertical else unit.width
        x, guard = origin, 0
        while x < span and guard < 100000:
            out.paste(unit, (0, x) if vertical else (x, 0))
            x += step
            guard += 1
        x, guard = origin - step, 0
        while x + step > 0 and guard < 100000:
            out.paste(unit, (0, x) if vertical else (x, 0))
            x -= step
            guard += 1

    if mode in ("lr_left", "lr_right"):
        frac = split if mode == "lr_left" else 1.0 - split
        cx = min(max(int(w * frac + 0.5), 1), w - 1)
        uw = 2 * cx
        unit = Image.new("RGBA", (uw, h), (0, 0, 0, 0))
        if mode == "lr_left":
            half = img.crop((0, 0, cx, h))
            unit.paste(half, (0, 0))
            unit.paste(half.transpose(FLIP_LR), (cx, 0))
            origin = 0
        else:
            half = img.crop((w - cx, 0, w, h))
            unit.paste(half.transpose(FLIP_LR), (0, 0))
            unit.paste(half, (cx, 0))
            origin = w - uw
        tile(unit, origin, w, False)
    elif mode in ("tb_top", "tb_bottom"):
        frac = split if mode == "tb_top" else 1.0 - split
        cy = min(max(int(h * frac + 0.5), 1), h - 1)
        uh = 2 * cy
        unit = Image.new("RGBA", (w, uh), (0, 0, 0, 0))
        if mode == "tb_top":
            half = img.crop((0, 0, w, cy))
            unit.paste(half, (0, 0))
            unit.paste(half.transpose(FLIP_TB), (0, cy))
            origin = 0
        else:
            half = img.crop((0, h - cy, w, h))
            unit.paste(half.transpose(FLIP_TB), (0, 0))
            unit.paste(half, (0, cy))
            origin = h - uh
        tile(unit, origin, h, True)

    return out


def load_frames(path):
    """读入图片或动图的全部帧。

    返回 ``(frames, durations, loop)``：
      * ``frames``    RGBA 帧列表，尺寸已经统一
      * ``durations`` 每帧毫秒数，与 frames 等长
      * ``loop``      循环次数，0 表示无限循环
    """
    with Image.open(path) as im:
        count = max(1, int(getattr(im, "n_frames", 1)))
        raw, durations = [], []
        for i in range(count):
            im.seek(i)
            try:
                frame = ImageOps.exif_transpose(im).convert("RGBA")
            except Exception:
                frame = im.convert("RGBA")
            raw.append(frame.copy())
            durations.append(
                max(20, int(im.info.get("duration", DEFAULT_DURATION) or DEFAULT_DURATION))
            )
        loop = int(im.info.get("loop", 0) or 0)

    size = (max(f.width for f in raw), max(f.height for f in raw))
    if any(f.size != size for f in raw):
        fixed = []
        for frame in raw:
            canvas = Image.new("RGBA", size, (0, 0, 0, 0))
            canvas.paste(frame, (0, 0))
            fixed.append(canvas)
        raw = fixed
    return raw, durations, loop


def fit_square(img: Image.Image, bg=(0, 0, 0, 0)) -> Image.Image:
    """用透明（或指定颜色）补边，把图变成正方形，内容居中。"""
    img = img.convert("RGBA")
    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), bg)
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    return canvas


def flatten_to_rgb(img: Image.Image, bg_rgb=(255, 255, 255)) -> Image.Image:
    """把透明区域压到纯色底上（JPG / BMP 不支持透明）。"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    base = Image.new("RGBA", img.size, tuple(bg_rgb) + (255,))
    return Image.alpha_composite(base, img).convert("RGB")


def resize_image(img: Image.Image, scale: float, square: bool = False) -> Image.Image:
    """按倍率缩放，可选补成正方形。"""
    if abs(scale - 1.0) > 1e-6:
        img = img.resize(
            (max(1, int(round(img.width * scale))), max(1, int(round(img.height * scale)))),
            RESAMPLE,
        )
    if square:
        img = fit_square(img)
    return img


def normalized_durations(durations, count) -> list:
    """把时长列表补齐/裁剪到 count 个，并保证每帧不小于 20ms。"""
    values = list(durations or [])
    out = []
    for i in range(count):
        raw = values[i] if i < len(values) else DEFAULT_DURATION
        try:
            ms = int(raw)
        except Exception:
            ms = DEFAULT_DURATION
        out.append(max(20, ms or DEFAULT_DURATION))
    return out


def save_gif(path, frames, durations=None, loop: int = 0, watermark: str | None = None) -> None:
    """保存为 GIF：多帧就是动画 GIF，单帧就是普通 GIF。

    ``watermark`` 会写进 GIF 的注释块（GIF 是调色板的，改像素会掉色）。
    """
    if not frames:
        raise ValueError("没有可保存的帧")
    frames = [f.convert("RGBA") for f in frames]
    meta = _wm.metadata_for("GIF", watermark) if watermark else {}
    if len(frames) == 1:
        frames[0].save(path, "GIF", **meta)
        return
    frames[0].save(
        path,
        "GIF",
        save_all=True,
        append_images=frames[1:],
        duration=normalized_durations(durations, len(frames)),
        loop=int(loop or 0),
        disposal=2,
        optimize=False,
        **meta,
    )


def save_webp(path, frames, durations=None, loop: int = 0, quality: int = 92,
              lossless: bool = False, watermark: str | None = None) -> None:
    """保存为 WebP：多帧就是动画 WebP，单帧就是普通 WebP。

    动画 + 透明要用无损模式，否则 libwebp 的帧间混合会在透明处留下残影。
    """
    if not frames:
        raise ValueError("没有可保存的帧")
    frames = [f.convert("RGBA") for f in frames]
    meta = _wm.metadata_for("WEBP", watermark) if watermark else {}
    if watermark and lossless:
        # 无损 WebP 像素不会被改，可以再叠一层像素最低位水印
        try:
            frames = [_wm.embed_lsb(f, watermark) for f in frames]
        except ValueError:
            pass
    if len(frames) == 1:
        if not lossless and watermark:
            frames[0].save(path, "WEBP", quality=quality, method=6, **meta)
        else:
            frames[0].save(path, "WEBP", quality=quality, method=6, lossless=bool(lossless), **meta)
        return
    frames[0].save(
        path,
        "WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=normalized_durations(durations, len(frames)),
        loop=int(loop or 0),
        lossless=bool(lossless),
        quality=quality,
        method=4,
        **meta,
    )


def checkerboard(size, cell: int = 10, light=(255, 255, 255), dark=(240, 241, 245)) -> Image.Image:
    """棋盘格底图，用来表示透明区域。"""
    w, h = max(1, int(size[0])), max(1, int(size[1]))
    img = Image.new("RGB", (w, h), light)
    draw = ImageDraw.Draw(img)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if ((x // cell) + (y // cell)) % 2:
                draw.rectangle(
                    [x, y, min(x + cell - 1, w - 1), min(y + cell - 1, h - 1)], fill=dark
                )
    return img


def export_frames(src_dir, out_dir, mode: str, split: float, scale: float = 1.0,
                  square: bool = False, on_progress=None, center_axis: bool = False,
                  target_size=None, watermark_text: str | None = None):
    """批量处理：把 src_dir 里的图片/动图全部对称化到 out_dir。

    返回 ``(ok, animated, failed)``。
    """
    src_dir, out_dir = Path(src_dir), Path(out_dir)
    files = sorted(
        p for p in src_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, animated, failed = 0, 0, []
    for index, src in enumerate(files, 1):
        try:
            frames, durations, loop = load_frames(src)
            results = [
                resize_image(make_symmetric(f, mode, split, center_axis), scale, square)
                for f in frames
            ]
            if target_size:
                size = (max(1, int(target_size[0])), max(1, int(target_size[1])))
                results = [r.resize(size, RESAMPLE) for r in results]
            payload = None
            if watermark_text:
                try:
                    payload = _wm.make_payload(watermark_text, results, durations)
                except Exception:
                    payload = None
            if len(results) > 1:
                save_gif(str(out_dir / f"{src.stem}.gif"), results, durations, loop,
                         watermark=payload)
                animated += 1
            else:
                meta = _wm.metadata_for("PNG", payload) if payload else {}
                img = results[0]
                if payload:
                    try:
                        img = _wm.embed_lsb(img, payload)
                    except ValueError:
                        pass
                img.save(str(out_dir / f"{src.stem}.png"), "PNG", **meta)
            ok += 1
        except Exception as exc:  # 单张失败不影响其它图片
            failed.append(f"{src.name}: {exc}")
        if on_progress is not None:
            on_progress(index, len(files), src.name)
    return ok, animated, failed
