# -*- coding: utf-8 -*-
"""核心引擎测试：像素级对称 + 动图往返。

运行： python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image  # noqa: E402

from mirror_symmetry import core  # noqa: E402


def make_image(w, h, seed=7):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    state = seed
    for y in range(h):
        for x in range(w):
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            px[x, y] = (state >> 16 & 255, state >> 8 & 255, state & 255, 255 if (x + y) % 3 else 0)
    return img


class TestMakeSymmetric(unittest.TestCase):
    def test_axis_symmetry_all_modes(self):
        for size in [(120, 80), (121, 81), (64, 64), (5, 4)]:
            w, h = size
            for mode in ("lr_left", "lr_right", "tb_top", "tb_bottom"):
                for split in (0.5, 0.25, 0.7):
                    out = core.make_symmetric(make_image(w, h), mode, split)
                    self.assertEqual(out.size, (w, h), f"{mode} {split} {size}")
                    frac = split if mode.endswith(("left", "top")) else 1.0 - split
                    if mode in ("lr_left", "lr_right"):
                        cx = min(max(int(w * frac + 0.5), 1), w - 1)
                        axis = cx if mode == "lr_left" else w - cx
                        px = out.load()
                        for x in range(w):
                            mirror = 2 * axis - 1 - x
                            if 0 <= mirror < w:
                                for y in range(0, h, 3):
                                    self.assertEqual(px[x, y], px[mirror, y], f"{mode} {split}")
                    else:
                        cy = min(max(int(h * frac + 0.5), 1), h - 1)
                        axis = cy if mode == "tb_top" else h - cy
                        px = out.load()
                        for y in range(h):
                            mirror = 2 * axis - 1 - y
                            if 0 <= mirror < h:
                                for x in range(0, w, 3):
                                    self.assertEqual(px[x, y], px[x, mirror], f"{mode} {split}")

    def test_centre_mirror_is_pixel_perfect(self):
        w, h = 100, 60
        src = make_image(w, h)
        for mode in ("lr_left", "lr_right"):
            px = core.make_symmetric(src, mode, 0.5).load()
            for x in range(w):
                for y in range(h):
                    self.assertEqual(px[x, y], px[w - 1 - x, y])
        for mode in ("tb_top", "tb_bottom"):
            px = core.make_symmetric(src, mode, 0.5).load()
            for x in range(w):
                for y in range(h):
                    self.assertEqual(px[x, y], px[x, h - 1 - y])

    def test_flip_modes(self):
        w, h = 33, 17
        src = make_image(w, h)
        sp = src.load()
        px = core.make_symmetric(src, "flip_h").load()
        self.assertTrue(all(px[x, y] == sp[w - 1 - x, y] for x in range(w) for y in range(h)))
        px = core.make_symmetric(src, "flip_v").load()
        self.assertTrue(all(px[x, y] == sp[x, h - 1 - y] for x in range(w) for y in range(h)))

    def test_kept_half_comes_from_source(self):
        w, h = 120, 40
        src = make_image(w, h)
        sp = src.load()
        left = core.make_symmetric(src, "lr_left", 0.5).load()
        self.assertTrue(all(left[x, y] == sp[x, y] for x in range(w // 2) for y in range(h)))
        right = core.make_symmetric(src, "lr_right", 0.5).load()
        self.assertTrue(
            all(right[x, y] == sp[x, y] for x in range(w // 2, w) for y in range(h))
        )

    def test_center_axis_output(self):
        """偏心时刻裁成对称尺寸，对称轴落在正中间。"""
        w, h = 240, 200
        src = make_image(w, h)
        for mode in ("lr_left", "lr_right", "tb_top", "tb_bottom"):
            for split in (0.35, 0.62, 0.8):
                out = core.make_symmetric(src, mode, split, center_axis=True)
                self.assertEqual(out.size, core.axis_centered_size(w, h, mode, split),
                                 f"{mode} {split}")
                px = out.load()
                W, H = out.size
                if mode in ("lr_left", "lr_right"):
                    for x in range(W // 2):
                        for y in range(0, H, 5):
                            self.assertEqual(px[x, y], px[W - 1 - x, y], f"{mode} {split}")
                else:
                    for y in range(H // 2):
                        for x in range(0, W, 5):
                            self.assertEqual(px[x, y], px[x, H - 1 - y], f"{mode} {split}")
            # 正中时不该改变尺寸
            out50 = core.make_symmetric(src, mode, 0.5, center_axis=True)
            self.assertEqual(out50.size, (w, h))

    def test_center_axis_keeps_source_half(self):
        src = make_image(100, 40)
        sp = src.load()
        out = core.make_symmetric(src, "lr_left", 0.3, center_axis=True)
        self.assertEqual(out.size, (60, 40))
        px = out.load()
        for x in range(30):
            for y in range(0, 40, 4):
                self.assertEqual(px[x, y], sp[x, y])
        for x in range(30, 60):
            for y in range(0, 40, 4):
                self.assertEqual(px[x, y], sp[59 - x, y])

    def test_tiny_images_do_not_crash(self):
        for size in [(1, 1), (1, 9), (9, 1), (2, 2)]:
            img = Image.new("RGBA", size, (1, 2, 3, 255))
            for mode in [m[0] for m in core.MODES]:
                out = core.make_symmetric(img, mode, 0.5)
                self.assertEqual(out.size, size)


class TestAnimation(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="mstest_"))

    def _gif(self, frames=5, durations=None):
        durations = durations or [60 + i * 20 for i in range(frames)]
        imgs = [core.make_symmetric(make_image(80, 60, seed=i + 1), "lr_left")
                for i in range(frames)]
        path = self.tmp / "anim.gif"
        core.save_gif(str(path), imgs, durations, 3)
        return path, durations

    def test_gif_roundtrip(self):
        path, durations = self._gif(5)
        frames, durs, loop = core.load_frames(path)
        self.assertEqual(len(frames), 5)
        self.assertEqual(loop, 3)
        self.assertEqual(durs[1], durations[1])

    def test_animated_gif_frames_stay_symmetric(self):
        path, _ = self._gif(4)
        frames, durs, loop = core.load_frames(path)
        out = self.tmp / "sym.gif"
        results = [core.make_symmetric(f, "lr_left", 0.5) for f in frames]
        core.save_gif(str(out), results, durs, loop)
        back, _, _ = core.load_frames(out)
        self.assertEqual(len(back), len(frames))
        px = back[2].load()
        for y in range(back[2].height):
            for x in range(back[2].width // 2):
                self.assertEqual(px[x, y], px[back[2].width - 1 - x, y])

    def test_lossless_webp_roundtrip(self):
        # 全不透明帧：无损 WebP 应当逐像素完全一致
        frames = [core.make_symmetric(make_image(64, 48, seed=i + 1).convert("RGB").convert("RGBA"), "tb_top")
                  for i in range(4)]
        path = self.tmp / "anim.webp"
        core.save_webp(str(path), frames, [80, 80, 80, 80], 0, lossless=True)
        got, _, _ = core.load_frames(path)
        self.assertEqual(len(got), 4)
        self.assertEqual(list(got[1].getdata()), list(frames[1].getdata()))

    def test_mismatched_frame_sizes_are_normalised(self):
        frames = [Image.new("RGBA", (40, 30), (255, 0, 0, 255)),
                  Image.new("RGBA", (20, 20), (0, 255, 0, 255))]
        path = self.tmp / "mixed.gif"
        core.save_gif(str(path), frames, [100, 100], 0)
        got, _, _ = core.load_frames(path)
        self.assertTrue(all(f.size == got[0].size for f in got))


class TestHelpers(unittest.TestCase):
    def test_fit_square_and_flatten(self):
        square = core.fit_square(Image.new("RGBA", (30, 10), (255, 0, 0, 128)))
        self.assertEqual(square.size, (30, 30))
        self.assertEqual(square.getpixel((0, 0)), (0, 0, 0, 0))
        flat = core.flatten_to_rgb(Image.new("RGBA", (2, 2), (0, 0, 255, 0)), (255, 255, 255))
        self.assertEqual(flat.mode, "RGB")
        self.assertEqual(flat.getpixel((0, 0)), (255, 255, 255))

    def test_resize_image(self):
        out = core.resize_image(Image.new("RGBA", (100, 50)), 0.5, True)
        self.assertEqual(out.size, (50, 50))
        out = core.resize_image(Image.new("RGBA", (100, 50)), 2.0, False)
        self.assertEqual(out.size, (200, 100))

    def test_normalized_durations(self):
        self.assertEqual(core.normalized_durations([100, 0, "x"], 4), [100, 100, 100, 100])
        self.assertEqual(len(core.normalized_durations([10], 3)), 3)

    def test_export_frames(self):
        src_dir = Path(tempfile.mkdtemp(prefix="mssrc_"))
        out_dir = Path(tempfile.mkdtemp(prefix="msout_"))
        Image.new("RGBA", (40, 20), (1, 2, 3, 255)).save(src_dir / "a.png")
        frames = []
        for i in range(3):
            f = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
            for x in range(5 + i * 8):
                for y in range(20):
                    f.putpixel((x, y), (9, 9, 9, 255))
            frames.append(f)
        core.save_gif(str(src_dir / "b.gif"), frames, [90] * 3, 0)
        ok, animated, failed = core.export_frames(src_dir, out_dir, "lr_left", 0.5)
        self.assertEqual((ok, animated, failed), (2, 1, []))
        self.assertTrue((out_dir / "a.png").exists())
        self.assertTrue((out_dir / "b.gif").exists())
        self.assertEqual(Image.open(out_dir / "b.gif").n_frames, 3)

        # 偏心 + 轴居中 + 自定义输出尺寸
        out2 = Path(tempfile.mkdtemp(prefix="msout2_"))
        ok2, anim2, failed2 = core.export_frames(
            src_dir, out2, "lr_left", 0.35, 1.0, False,
            center_axis=True, target_size=(120, 60),
        )
        self.assertEqual((ok2, anim2, failed2), (2, 1, []))
        self.assertEqual(Image.open(out2 / "a.png").size, (120, 60))
        gif_out = Image.open(out2 / "b.gif")
        self.assertEqual(gif_out.size, (120, 60))
        self.assertEqual(gif_out.n_frames, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
