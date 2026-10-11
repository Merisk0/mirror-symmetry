# -*- coding: utf-8 -*-
"""中英文文案。

静态文案用「中文原文 -> 英文」查表（界面构建完成后统一替换），
动态文案（状态栏、提示、对话框）用 msg() 按 key 取。
"""

from __future__ import annotations

LANG_NAMES = {"zh": "中文", "en": "English"}
LANGS = ("zh", "en")

# --------------------------------------------------------------------------- #
#  静态文案：键是界面里写的中文原文
# --------------------------------------------------------------------------- #
STATIC_EN = {
    "对称表情包生成器": "Mirror Symmetry Studio",
    # 顶部按钮
    "打开图片": "Open",
    "粘贴": "Paste",
    "批量处理": "Batch",
    "另存为…": "Save as…",
    "保存结果": "Save",
    # 卡片标题
    "对称方式": "Symmetry mode",
    "对称轴位置": "Mirror axis",
    "动图": "Animation",
    "导出设置": "Export",
    # 对称方式
    "左半镜像到右边": "Left → right",
    "右半镜像到左边": "Right → left",
    "上半镜像到下边": "Top → bottom",
    "下半镜像到上边": "Bottom → top",
    "整图左右翻转": "Flip horizontal",
    "整图上下翻转": "Flip vertical",
    # 对称轴
    "回到正中": "Centre",
    "偏离正中时，图案会平铺成万花筒效果。": "Off-centre tiles the pattern like a kaleidoscope.",
    # 动图
    "播放动画预览": "Play preview",
    "空格": "Space",
    # 导出
    "倍率": "Scale",
    "对称轴居中输出": "Centre axis in output",
    "输出尺寸": "Output size",
    "自动": "Auto",
    "自定义": "Custom",
    "宽": "W",
    "高": "H",
    "补成正方形（透明边）": "Square canvas (transparent)",
    "JPG/BMP 底色": "JPG/BMP background",
    "选择": "Choose",
    "动图存 GIF / WebP 保留动画，存 PNG/JPG 只存当前帧。":
        "GIF/WebP keep the animation; PNG/JPG save the current frame only.",
    "偏心时自动裁成对称尺寸，让对称轴落在正中间。":
        "When off-centre, crop to the symmetric size so the axis lands in the middle.",
    # 预览
    "原图": "Source",
    "对称结果": "Result",
    "拖入图片 / GIF\n\n或点击右上角「打开图片」":
        "Drop an image or GIF here\n\nor click “Open” at the top right",
    "对称结果会显示在这里\n\n动图会逐帧镜像并播放":
        "The mirrored result shows here\n\nGIFs are mirrored frame by frame",
    "对称轴": "axis",
    "支持 PNG · JPG · WebP · GIF(动图) · BMP": "PNG · JPG · WebP · GIF · BMP",
    # 菜单 / 关于
    "关于本软件": "About",
    "打开设置目录": "Open settings folder",
    "清空图片": "Clear image",
    "退出": "Quit",
    "好": "OK",
    "语言 / Language": "语言 / Language",
    "界面缩放": "UI scale",
    # 文件对话框
    "图片 / 动图": "Images / GIF",
    "GIF 动图": "Animated GIF",
    "所有文件": "All files",
    "动画 GIF（保留动画）": "Animated GIF (keeps animation)",
    "动画 WebP（动画 + 透明）": "Animated WebP (animation + alpha)",
    "WebP 图片（支持透明）": "WebP (supports alpha)",
    "PNG 图片（支持透明）": "PNG (supports alpha)",
    "JPEG 图片": "JPEG",
    "BMP 图片": "BMP",
    "GIF 图片": "GIF",
}

# --------------------------------------------------------------------------- #
#  动态文案
# --------------------------------------------------------------------------- #
MESSAGES = {
    "zh": {
        "app_title": "对称表情包生成器",
        "ready": "拖入图片或 GIF，或者点「打开图片」开始 —— 默认取左半镜像到右边。",
        "loaded": "已载入 {name} —— {w}×{h}",
        "loaded_anim": "已载入 {name} —— {w}×{h} · 动图 {n} 帧，正在播放",
        "clip_empty": "剪贴板里没有图片。可以先 Win+Shift+S 截图，再按 Ctrl+V。",
        "clip_no_file": "剪贴板里是文件路径，但没有找到图片文件。",
        "pasted": "已从剪贴板粘贴图片 —— {w}×{h}",
        "cleared": "已清空，重新打开一张图片或 GIF 吧。",
        "opened_failed": "打不开这个文件：\n{path}\n\n{err}",
        "saved": "已保存 {name}",
        "saved_anim": "已保存 {name}（动画 {n} 帧）",
        "saved_static": "已保存 {name}（动图只导出了当前帧，要保留动画请存 GIF / WebP）",
        "save_failed": "保存失败：\n{err}",
        "no_image": "还没有图片，先打开或粘贴一张吧。",
        "chip_gif": "GIF · {n} 帧",
        "chip_static": "静态图",
        "axis_centre": "正中 50%",
        "axis_custom": "轴位 {v:.0f}%",
        "frame_info": "第 {i} / {n} 帧 · 每帧 {ms} ms · 循环 {loop}",
        "loop_forever": "无限",
        "mode_lr_left": "取左半 -> 镜像到右边",
        "mode_lr_right": "取右半 -> 镜像到左边",
        "mode_tb_top": "取上半 -> 镜像到下边",
        "mode_tb_bottom": "取下半 -> 镜像到上边",
        "mode_flip_h": "整张图片左右翻转",
        "mode_flip_v": "整张图片上下翻转",
        "anim_frames": "动画 {n} 帧",
        "export_size": "导出 {w}×{h}",
        "auto_size": "自动 {w}×{h}",
        "batch_title": "批量处理文件夹",
        "batch_confirm": "将处理 {n} 个文件（含 GIF 动图）\n方式：{mode}\n对称轴：{axis:.0f}%　倍率：{scale:.0f}%{square}\n\n动图 → 动画 GIF，静态图 → PNG\n输出到：{out}",
        "batch_square": "（补正方形）",
        "batch_none": "这个文件夹里没有找到图片。",
        "batch_running": "批量处理中…",
        "batch_prepare": "准备中…",
        "batch_progress": "正在处理 {i} / {n}",
        "batch_done": "完成！成功 {ok} 个（其中动图 {anim} 个），失败 {bad} 个。\n\n输出目录：\n{out}",
        "batch_failed": "\n\n失败列表（最多显示 8 条）：\n{list}",
        "batch_finished": "批量完成 —— {out}",
        "batch_open_q": "\n\n现在打开输出文件夹吗？",
        "batch_start_q": "开始吗？",
        "about_body": "把图片或 GIF 从中间切开，取一半镜像到另一半。\n· 六种对称方式，对称轴可自由调整\n· 偏心时可选「轴居中输出」，轴永远在正中间\n· GIF 逐帧对称，保留帧时长与循环次数\n· 导出 PNG / JPG / WebP / 动画 GIF / BMP\n· 批量处理整个文件夹\n\n快捷键：Ctrl+O 打开　Ctrl+V 粘贴　Ctrl+S 保存\n　　　　Ctrl+R 清空　空格 播放/暂停　方向键 切换方式",
        "about_title": "关于 {app}",
        "menu_language": "语言 / Language",
        "open_title": "选择图片或动图",
        "save_title": "保存对称结果",
        "batch_pick": "选择要批量处理的文件夹",
        "paste_label": "剪贴板图片",
        "size_chip": "{w}×{h}",
    },
    "en": {
        "app_title": "Mirror Symmetry Studio",
        "ready": "Drop an image or GIF here, or click Open — default: mirror the left half to the right.",
        "loaded": "Loaded {name} — {w}×{h}",
        "loaded_anim": "Loaded {name} — {w}×{h} · {n}-frame animation, playing",
        "clip_empty": "No image in the clipboard. Press Win+Shift+S to grab one, then Ctrl+V.",
        "clip_no_file": "The clipboard holds file paths, but no image files.",
        "pasted": "Pasted from clipboard — {w}×{h}",
        "cleared": "Cleared — open another image or GIF.",
        "opened_failed": "Cannot open this file:\n{path}\n\n{err}",
        "saved": "Saved {name}",
        "saved_anim": "Saved {name} ({n}-frame animation)",
        "saved_static": "Saved {name} (only the current frame — use GIF/WebP to keep the animation)",
        "save_failed": "Save failed:\n{err}",
        "no_image": "Nothing to save yet — open or paste an image first.",
        "chip_gif": "GIF · {n} frames",
        "chip_static": "Still image",
        "axis_centre": "Centre 50%",
        "axis_custom": "Axis {v:.0f}%",
        "frame_info": "Frame {i} / {n} · {ms} ms · loop {loop}",
        "loop_forever": "forever",
        "mode_lr_left": "Left half → right",
        "mode_lr_right": "Right half → left",
        "mode_tb_top": "Top half → bottom",
        "mode_tb_bottom": "Bottom half → top",
        "mode_flip_h": "Flip horizontal",
        "mode_flip_v": "Flip vertical",
        "anim_frames": "{n}-frame animation",
        "export_size": "export {w}×{h}",
        "auto_size": "Auto {w}×{h}",
        "batch_title": "Batch a folder",
        "batch_confirm": "Will process {n} files (GIFs included)\nMode: {mode}\nAxis: {axis:.0f}%　Scale: {scale:.0f}%{square}\n\nGIF → animated GIF, stills → PNG\nOutput: {out}",
        "batch_square": " (square)",
        "batch_none": "No images found in this folder.",
        "batch_running": "Processing…",
        "batch_prepare": "Preparing…",
        "batch_progress": "Processing {i} / {n}",
        "batch_done": "Done! {ok} succeeded ({anim} animations), {bad} failed.\n\nOutput:\n{out}",
        "batch_failed": "\n\nFailures (first 8):\n{list}",
        "batch_finished": "Batch finished — {out}",
        "batch_open_q": "\n\nOpen the output folder now?",
        "batch_start_q": "Start?",
        "about_body": "Cut an image or GIF down the middle and mirror one half onto the other.\n· Six symmetry modes, free axis position\n· ‘Centre axis in output’ keeps the axis dead centre\n· Frame-by-frame GIF mirroring, timing and loop preserved\n· Export PNG / JPG / WebP / animated GIF / BMP\n· Batch a whole folder\n\nShortcuts: Ctrl+O open　Ctrl+V paste　Ctrl+S save\n　　　　　 Ctrl+R clear　Space play/pause　Arrows switch mode",
        "about_title": "About {app}",
        "menu_language": "Language / 语言",
        "open_title": "Choose an image or GIF",
        "save_title": "Save result",
        "batch_pick": "Choose a folder to batch",
        "paste_label": "Clipboard image",
        "size_chip": "{w}×{h}",
    },
}


def msg(lang: str, key: str, **kwargs) -> str:
    """取动态文案并格式化。"""
    table = MESSAGES.get(lang) or MESSAGES["zh"]
    text = table.get(key)
    if text is None:
        text = MESSAGES["zh"].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def static_map(lang: str) -> dict:
    """静态文案替换表。

    英文返回「中文 -> English」，中文返回反向表，
    这样中英切换来回都能替换。
    """
    if str(lang).lower().startswith("en"):
        return STATIC_EN
    return {v: k for k, v in STATIC_EN.items()}


def mode_label(lang: str, mode: str) -> str:
    return msg(lang, f"mode_{mode}")
