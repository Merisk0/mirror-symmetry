# -*- coding: utf-8 -*-
"""隐藏水印（隐形水印）——把一段信息不可见地写进导出的图片里。

两种载体，按格式自动选择：

* **像素最低位（LSB）**：PNG / BMP / 无损 WebP。每个像素的 R/G/B 最低位各藏 1 bit，
  肉眼完全看不出（每通道最多差 1，远低于可见阈值），用普通看图软件也看不出来。
* **元数据**：GIF（注释块）、JPEG（COM 段）、WebP（XMP）。这些格式要么有损、要么调色板化，
  改像素会被破坏或引起色偏，所以走元数据；同样是"看不见"的。

水印内容形如：``MSW1|文字|时间|宽x高x帧数|指纹|crc``（共 6 段）。

* ``MSW1`` 是版本魔数，用来识别"这确实是我们写的水印"
* ``指纹`` 是导出内容的 SHA-256 前 16 位，用于核对是不是同一份图
* ``crc`` 做校验，读坏了就直接判定为无效
"""

from __future__ import annotations

import hashlib
import re
import zlib
from datetime import datetime

from PIL import Image, PngImagePlugin

__all__ = [
    "MAGIC",
    "make_payload",
    "parse_payload",
    "embed_lsb",
    "extract_lsb",
    "metadata_for",
    "read_metadata",
    "read_watermark",
    "signature_for",
]

MAGIC = "MSW1"
MAX_PAYLOAD = 4096
XMP_KEY = "ms:watermark"


# --------------------------------------------------------------------------- #
#  水印内容
# --------------------------------------------------------------------------- #
def signature_for(frames, durations=None) -> str:
    """给这次导出的内容算一个指纹（尺寸 + 帧数 + 总时长 + 首帧像素）。"""
    if not frames:
        return "0" * 16
    first = frames[0].convert("RGBA")
    digest = hashlib.sha256()
    digest.update(f"{first.width}x{first.height}|{len(frames)}|".encode())
    digest.update(str(sum(int(d or 0) for d in (durations or []))).encode())
    digest.update(first.tobytes())
    return digest.hexdigest()[:16]


def make_payload(text: str, frames=None, durations=None, when: datetime | None = None) -> str:
    """拼出水印字符串。"""
    text = (text or "").strip().replace("|", "/")[:120]
    when = when or datetime.now()
    stamp = when.strftime("%Y-%m-%d %H:%M")
    if frames:
        first = frames[0]
        size = f"{first.width}x{first.height}x{len(frames)}"
        sig = signature_for(frames, durations)
    else:
        size, sig = "-", "0" * 16
    body = f"{MAGIC}|{text}|{stamp}|{size}|{sig}"
    crc = zlib.crc32(body.encode("utf-8")) & 0xFFFFFFFF
    return f"{body}|{crc:08x}"


def parse_payload(payload: str) -> dict | None:
    """解析并校验水印，失败返回 None。"""
    if not payload or not payload.startswith(MAGIC + "|"):
        return None
    parts = payload.split("|")
    if len(parts) != 6:
        return None
    body = "|".join(parts[:-1])
    try:
        crc = int(parts[-1], 16)
    except ValueError:
        return None
    if (zlib.crc32(body.encode("utf-8")) & 0xFFFFFFFF) != crc:
        return None
    return {
        "magic": parts[0],
        "text": parts[1],
        "time": parts[2],
        "size": parts[3],
        "signature": parts[4],
        "raw": payload,
    }


# --------------------------------------------------------------------------- #
#  像素最低位（LSB）
# --------------------------------------------------------------------------- #
def _bits_from(data: bytes):
    for byte in data:
        for shift in range(7, -1, -1):
            yield (byte >> shift) & 1


def _bytes_from(bits) -> bytes:
    out = bytearray()
    for i in range(0, len(bits) - 7, 8):
        value = 0
        for bit in bits[i:i + 8]:
            value = (value << 1) | bit
        out.append(value)
    return bytes(out)


def embed_lsb(img: Image.Image, payload: str) -> Image.Image:
    """把 payload 写进可见像素的 R/G/B 最低位，返回新图；容量不够会抛 ValueError。"""
    data = payload.encode("utf-8")
    if len(data) > MAX_PAYLOAD:
        raise ValueError("水印太长了")
    stream = len(data).to_bytes(2, "big") + data
    bits = list(_bits_from(stream))
    total = len(bits)

    out = img.convert("RGBA").copy()
    px = out.load()
    w, h = out.size
    idx = 0
    for y in range(h):
        if idx >= total:
            break
        for x in range(w):
            if idx >= total:
                break
            r, g, b, a = px[x, y]
            chans = [r, g, b]
            for k in range(3):
                if idx >= total:
                    break
                chans[k] = (chans[k] & 0xFE) | bits[idx]
                idx += 1
            px[x, y] = (chans[0], chans[1], chans[2], a)

    if idx < total:
        raise ValueError("图片太小，放不下水印（换大一点的图或用元数据）")
    return out


def extract_lsb(img: Image.Image, frames_to_try: int = 3) -> str | None:
    """从像素最低位读回水印；读不到返回 None。"""
    im = img
    try:
        n_frames = int(getattr(im, "n_frames", 1))
    except Exception:
        n_frames = 1
    for index in range(min(n_frames, max(1, frames_to_try))):
        try:
            if n_frames > 1:
                im.seek(index)
        except Exception:
            pass
        frame = im.convert("RGBA")
        px = frame.load()
        w, h = frame.size
        bits: list[int] = []
        for y in range(h):
            for x in range(w):
                r, g, b, _a = px[x, y]
                bits.extend((r & 1, g & 1, b & 1))
                if len(bits) >= 16:
                    break
            if len(bits) >= 16:
                break
        if len(bits) < 16:
            continue
        length = int.from_bytes(_bytes_from(bits[:16]), "big")
        if length <= 0 or length > MAX_PAYLOAD:
            continue
        need = 16 + length * 8
        collected: list[int] = []
        for y in range(h):
            for x in range(w):
                r, g, b, _a = px[x, y]
                collected.extend((r & 1, g & 1, b & 1))
            if len(collected) >= need:
                break
        if len(collected) < need:
            continue
        try:
            text = _bytes_from(collected[16:need]).decode("utf-8")
        except UnicodeDecodeError:
            continue
        if text.startswith(MAGIC + "|"):
            return text
    return None


# --------------------------------------------------------------------------- #
#  元数据载体
# --------------------------------------------------------------------------- #
def _xmp_bytes(payload: str) -> bytes:
    safe = payload.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
    xml = (
        '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description xmlns:ms="https://merisk.top/ns/mirror-symmetry/1.0/" '
        f'{XMP_KEY}="{safe}"/>'
        "</rdf:RDF></x:xmpmeta>"
        '<?xpacket end="w"?>'
    )
    return xml.encode("utf-8")


def _pnginfo(payload: str) -> PngImagePlugin.PngInfo:
    info = PngImagePlugin.PngInfo()
    info.add_text("MirrorSymmetry", payload)
    info.add_text("Software", "Mirror Symmetry Studio")
    return info


def metadata_for(fmt: str, payload: str) -> dict:
    """按格式返回 save() 需要的元数据参数。"""
    fmt = (fmt or "").upper()
    if fmt == "PNG":
        return {"pnginfo": _pnginfo(payload)}
    if fmt in ("JPEG", "JPG", "GIF"):
        return {"comment": payload.encode("utf-8")}
    if fmt == "WEBP":
        return {"xmp": _xmp_bytes(payload)}
    return {}


def read_metadata(path) -> str | None:
    """从文件元数据里读水印。"""
    try:
        with Image.open(path) as im:
            info = dict(getattr(im, "info", {}) or {})
            # PNG tEXt
            for key in ("MirrorSymmetry", "mirrorsymmetry", "Software"):
                value = info.get(key)
                if isinstance(value, bytes):
                    value = value.decode("utf-8", "ignore")
                if isinstance(value, str) and value.startswith(MAGIC + "|"):
                    return value
            # GIF / JPEG 注释
            comment = info.get("comment")
            if isinstance(comment, (bytes, bytearray)):
                comment = bytes(comment).decode("utf-8", "ignore")
            if isinstance(comment, str) and comment.startswith(MAGIC + "|"):
                return comment
            # WebP XMP
            xmp = info.get("xmp") or info.get("XML:com.adobe.xmp")
            if isinstance(xmp, (bytes, bytearray)):
                xmp = bytes(xmp).decode("utf-8", "ignore")
            if isinstance(xmp, str):
                hit = re.search(rf'{XMP_KEY}="(.*?)"', xmp, re.S)
                if hit:
                    value = (hit.group(1).replace("&quot;", '"')
                             .replace("&lt;", "<").replace("&amp;", "&"))
                    if value.startswith(MAGIC + "|"):
                        return value
    except Exception:
        return None
    return None


def read_watermark(path) -> dict | None:
    """读水印：先看元数据，再看像素最低位。返回 parse_payload 的结果。"""
    payload = read_metadata(path)
    method = "metadata"
    if not payload:
        try:
            with Image.open(path) as im:
                payload = extract_lsb(im)
            method = "lsb"
        except Exception:
            payload = None
    if not payload:
        return None
    parsed = parse_payload(payload)
    if parsed:
        parsed["method"] = method
    return parsed
