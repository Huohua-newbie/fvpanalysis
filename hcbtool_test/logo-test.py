# -*- coding: utf-8 -*-
"""Approximate recreation of Sakura's logo presentation function `f_00074DA5`.

Features
--------
1. Reads external image files from an assets directory.
2. Replays a motion sequence based on the current reverse-engineering notes.
3. Supports skip behavior by keyboard / mouse input.

This is a *reference recreation*, not a byte-accurate FVP runtime clone.
The motion system is mapped to a small 2D animation engine using `tkinter`
+ `Pillow`, with the following approximations:

- `PrimSetOP` -> local 2D position (center anchor)
- `PrimSetAlpha` / `MotionAlpha` -> per-layer alpha
- `MotionMoveR` -> rotation in tenths of degrees
- `MotionMoveS2` -> independent width / height scale factors (1000 == 1.0)
- `MotionMoveZ` -> a subtle depth-driven scale change
- `MotionMove` -> XY translation tween

Usage
-----
python logo演出.py --assets ./logo_assets

Expected default asset filenames
-------------------------------
- logo_bg.png
- logo_favo.png
- logo_favo_view.png
- logo_favo_view_p1.png
- logo_favo_view_p2.png
- logo_favo_view_p3.png

If a file is missing, a colored placeholder image is generated so the
animation logic can still be observed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import argparse
import time
import tkinter as tk

from PIL import Image, ImageDraw, ImageFont, ImageTk


try:
    RESAMPLE_BICUBIC = Image.Resampling.BICUBIC
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:  # Pillow < 9
    RESAMPLE_BICUBIC = Image.BICUBIC
    RESAMPLE_LANCZOS = Image.LANCZOS


WINDOW_W = 1280
WINDOW_H = 720
BACKGROUND_COLOR = "#000000"
DEFAULT_ASSET_DIR = Path(__file__).with_name("logo_assets")
FACTOR_DENOM = 1000.0
ENGINE_DEPTH_BASE_Z = 1000.0
FRAME_MS = 16

# HZC image built-in offsets supplied by reverse-engineering notes.
# Values are little-endian 16-bit integers from the resource headers.
LOGO_HZC_TOP_LEFT = {
    "logo_bg": (0x0000, 0x0000),
    "logo_favo": (0x01CF, 0x0104),
    "logo_favo_view": (0x021B, 0x0196),
    "logo_favo_view_p1": (0x026A, 0x0199),
    "logo_favo_view_p2": (0x026A, 0x0194),
    "logo_favo_view_p3": (0x026A, 0x0190),
}


@dataclass
class LayerState:
    key: str
    slot: int
    image: Image.Image
    x: float
    y: float
    pivot_x: float = 0.0
    pivot_y: float = 0.0
    alpha: float = 255.0
    rotation_tenths: float = 0.0
    scale_x_factor: float = 1000.0
    scale_y_factor: float = 1000.0
    z_value: float = 1000.0
    depth_enabled: bool = False
    order: int = 0
    canvas_item: int | None = None
    photo: ImageTk.PhotoImage | None = None


@dataclass
class Tween:
    layer_key: str
    attr: str
    src: float | None
    dst: float | None
    start_ms: float
    duration_ms: float
    mode: int = 0
    finished: bool = False
    _resolved: bool = False

    def resolve(self, layer: LayerState) -> None:
        if self._resolved:
            return
        if self.src is None:
            self.src = float(getattr(layer, self.attr))
        if self.dst is None:
            self.dst = float(getattr(layer, self.attr))
        self._resolved = True

    def _eased_progress(self, linear_t: float) -> float:
        if self.mode == 1:
            return 1.0
        if self.mode == 3:
            # Use an ease-out cubic curve as a practical approximation of the
            # FVP motion type used by this logo sequence.
            return 1.0 - (1.0 - linear_t) ** 3
        return linear_t

    def apply(self, now_ms: float, layer: LayerState) -> None:
        if self.finished or now_ms < self.start_ms:
            return
        self.resolve(layer)
        assert self.src is not None and self.dst is not None
        if self.duration_ms <= 0:
            setattr(layer, self.attr, self.dst)
            self.finished = True
            return
        linear_t = max(0.0, min(1.0, (now_ms - self.start_ms) / self.duration_ms))
        eased_t = self._eased_progress(linear_t)
        value = self.src + (self.dst - self.src) * eased_t
        setattr(layer, self.attr, value)
        if linear_t >= 1.0:
            setattr(layer, self.attr, self.dst)
            self.finished = True


def alpha_to_int(alpha: float) -> int:
    return max(0, min(255, int(round(alpha))))


def compute_depth_scale(z_value: float) -> float:
    z = max(100.0, float(z_value))
    return ENGINE_DEPTH_BASE_Z / z


def placeholder_color(key: str) -> tuple[int, int, int, int]:
    table = {
        "logo_bg": (36, 40, 60, 255),
        "logo_favo": (244, 210, 80, 255),
        "logo_favo_view": (100, 160, 255, 255),
        "logo_favo_view_p1": (255, 120, 120, 255),
        "logo_favo_view_p2": (120, 255, 170, 255),
        "logo_favo_view_p3": (180, 140, 255, 255),
    }
    return table.get(key, (180, 180, 180, 255))


def create_placeholder(key: str, size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGBA", size, placeholder_color(key))
    draw = ImageDraw.Draw(image)
    label = f"{key}\n(MISSING)"
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    bbox = draw.multiline_textbbox((0, 0), label, font=font, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.multiline_text(
        ((size[0] - text_w) / 2, (size[1] - text_h) / 2),
        label,
        fill=(255, 255, 255, 255),
        font=font,
        align="center",
    )
    return image


def load_image(asset_dir: Path, filename: str, key: str, fallback_size: tuple[int, int]) -> Image.Image:
    path = asset_dir / filename
    if path.exists():
        return Image.open(path).convert("RGBA")
    return create_placeholder(key, fallback_size)


def anchor_center_from_top_left(image: Image.Image, left: float, top: float) -> tuple[float, float]:
    return left + image.width / 2.0, top + image.height / 2.0



def build_layers(asset_dir: Path) -> dict[str, LayerState]:
    asset_map = {
        "logo_bg": ("logo_bg.png", (WINDOW_W, WINDOW_H)),
        "logo_favo": ("logo_favo.png", (800, 320)),
        "logo_favo_view": ("logo_favo_view.png", (800, 320)),
        "logo_favo_view_p1": ("logo_favo_view_p1.png", (260, 220)),
        "logo_favo_view_p2": ("logo_favo_view_p2.png", (260, 220)),
        "logo_favo_view_p3": ("logo_favo_view_p3.png", (260, 220)),
    }
    images = {
        key: load_image(asset_dir, filename, key, fallback)
        for key, (filename, fallback) in asset_map.items()
    }

    def pos_for(key: str) -> tuple[float, float]:
        left, top = LOGO_HZC_TOP_LEFT[key]
        return anchor_center_from_top_left(images[key], left, top)

    bg_x, bg_y = pos_for("logo_bg")
    favo_x, favo_y = pos_for("logo_favo")
    view_x, view_y = pos_for("logo_favo_view")
    p1_x, p1_y = pos_for("logo_favo_view_p1")
    p2_x, p2_y = pos_for("logo_favo_view_p2")
    p3_x, p3_y = pos_for("logo_favo_view_p3")

    return {
        "logo_bg": LayerState(
            key="logo_bg",
            slot=250,
            image=images["logo_bg"],
            x=bg_x,
            y=bg_y,
            alpha=255,
            depth_enabled=False,
            order=0,
        ),
        "logo_favo": LayerState(
            key="logo_favo",
            slot=252,
            image=images["logo_favo"],
            x=favo_x,
            y=favo_y,
            alpha=0,
            z_value=750,
            depth_enabled=True,
            order=1,
        ),
        "logo_favo_view": LayerState(
            key="logo_favo_view",
            slot=254,
            image=images["logo_favo_view"],
            x=view_x,
            y=view_y,
            alpha=0,
            z_value=750,
            depth_enabled=True,
            order=2,
        ),
        "logo_favo_view_p1": LayerState(
            key="logo_favo_view_p1",
            slot=255,
            image=images["logo_favo_view_p1"],
            x=p1_x,
            y=p1_y,
            alpha=0,
            rotation_tenths=3600,
            scale_x_factor=5000,
            scale_y_factor=5000,
            order=3,
        ),
        "logo_favo_view_p2": LayerState(
            key="logo_favo_view_p2",
            slot=256,
            image=images["logo_favo_view_p2"],
            x=p2_x,
            y=p2_y,
            alpha=0,
            rotation_tenths=3600,
            scale_x_factor=5000,
            scale_y_factor=5000,
            order=4,
        ),
        "logo_favo_view_p3": LayerState(
            key="logo_favo_view_p3",
            slot=257,
            image=images["logo_favo_view_p3"],
            x=p3_x,
            y=p3_y,
            alpha=0,
            rotation_tenths=-3600,
            scale_x_factor=5000,
            scale_y_factor=5000,
            order=5,
        ),
    }


class LogoSequencePlayer:
    def __init__(self, root: tk.Tk, asset_dir: Path, auto_close: bool = False):
        self.root = root
        self.asset_dir = asset_dir
        self.auto_close = auto_close
        self.layers = build_layers(asset_dir)
        self.tweens: list[Tween] = []
        self.started_at = time.perf_counter()
        self.skip_requested = False
        self.state = "intro"
        self.state_enter_ms = 0.0
        self.final_fade_end_ms = 0.0
        self.quick_cleanup_end_ms = 0.0
        self.sequence_finished = False

        self.root.title("FVP LOGO 演出复现")
        self.root.configure(bg=BACKGROUND_COLOR)
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            self.root,
            width=WINDOW_W,
            height=WINDOW_H,
            bg=BACKGROUND_COLOR,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.hint_var = tk.StringVar(value="点击鼠标、空格、回车或 Esc 可跳过")
        self.hint_label = tk.Label(
            self.root,
            textvariable=self.hint_var,
            bg="#000000",
            fg="#FFFFFF",
            font=("Microsoft YaHei UI", 10),
        )
        self.hint_label.place(x=12, y=WINDOW_H - 30)

        self.debug_var = tk.StringVar(value=f"assets: {asset_dir}")
        self.debug_label = tk.Label(
            self.root,
            textvariable=self.debug_var,
            bg="#000000",
            fg="#A0A0A0",
            font=("Consolas", 9),
        )
        self.debug_label.place(x=12, y=8)

        self.root.bind("<space>", self.request_skip)
        self.root.bind("<Return>", self.request_skip)
        self.root.bind("<Escape>", self.request_skip)
        self.root.bind("<Button-1>", self.request_skip)

        for layer in sorted(self.layers.values(), key=lambda x: x.order):
            layer.canvas_item = self.canvas.create_image(0, 0, anchor="nw")

        self.setup_intro_tweens()
        self.tick()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self.started_at) * 1000.0

    def request_skip(self, _event=None):
        self.skip_requested = True
        self.hint_var.set("已请求跳过，正在进入收尾阶段…")

    def add_tween(self, tween: Tween):
        self.tweens.append(tween)

    def schedule_alpha(self, layer: str, src: float | None, dst: float | None, start: float, duration: float, mode: int = 0):
        self.add_tween(Tween(layer, "alpha", src, dst, start, duration, mode))

    def schedule_rotation(self, layer: str, src: float | None, dst: float | None, start: float, duration: float, mode: int = 3):
        self.add_tween(Tween(layer, "rotation_tenths", src, dst, start, duration, mode))

    def schedule_x(self, layer: str, src: float | None, dst: float | None, start: float, duration: float, mode: int = 3):
        self.add_tween(Tween(layer, "x", src, dst, start, duration, mode))

    def schedule_y(self, layer: str, src: float | None, dst: float | None, start: float, duration: float, mode: int = 3):
        self.add_tween(Tween(layer, "y", src, dst, start, duration, mode))

    def schedule_z(self, layer: str, src: float | None, dst: float | None, start: float, duration: float, mode: int = 3):
        self.add_tween(Tween(layer, "z_value", src, dst, start, duration, mode))

    def schedule_scale_x(self, layer: str, src: float | None, dst: float | None, start: float, duration: float, mode: int = 3):
        self.add_tween(Tween(layer, "scale_x_factor", src, dst, start, duration, mode))

    def schedule_scale_y(self, layer: str, src: float | None, dst: float | None, start: float, duration: float, mode: int = 3):
        self.add_tween(Tween(layer, "scale_y_factor", src, dst, start, duration, mode))

    def setup_intro_tweens(self):
        start = 0.0
        duration = 2000.0
        main_duration = 1800.0

        # p3
        self.schedule_alpha("logo_favo_view_p3", 0, 255, start, duration, 0)
        self.schedule_rotation("logo_favo_view_p3", -3600, 0, start, duration, 3)
        self.schedule_scale_x("logo_favo_view_p3", 5000, 1000, start, duration, 3)
        self.schedule_scale_y("logo_favo_view_p3", 5000, 1000, start, duration, 3)

        # p2
        self.schedule_alpha("logo_favo_view_p2", 0, 255, start, duration, 0)
        self.schedule_rotation("logo_favo_view_p2", 3600, 0, start, duration, 3)
        self.schedule_scale_x("logo_favo_view_p2", 5000, 1000, start, duration, 3)
        self.schedule_scale_y("logo_favo_view_p2", 5000, 1000, start, duration, 3)

        # p1
        self.schedule_alpha("logo_favo_view_p1", 0, 255, start, duration, 0)
        self.schedule_rotation("logo_favo_view_p1", 3600, 0, start, duration, 3)
        self.schedule_scale_x("logo_favo_view_p1", 5000, 1000, start, duration, 3)
        self.schedule_scale_y("logo_favo_view_p1", 5000, 1000, start, duration, 3)

        # main logo
        self.schedule_z("logo_favo", 750, 1000, start, main_duration, 3)
        self.schedule_alpha("logo_favo", 0, 255, start, main_duration, 0)

        # view layer
        self.schedule_z("logo_favo_view", 750, 1000, start, duration, 3)
        view_base_y = self.layers["logo_favo_view"].y
        self.schedule_y("logo_favo_view", view_base_y + 50, view_base_y, start, duration, 3)
        self.schedule_alpha("logo_favo_view", 0, 255, start, duration, 0)

    def start_background_fade(self, now_ms: float):
        self.schedule_alpha("logo_bg", None, 0, now_ms, 3500.0, 0)
        self.state = "post_intro_wait"
        self.state_enter_ms = now_ms
        self.hint_var.set("LOGO 主演出完成，背景淡出中；可继续跳过")

    def start_final_fade(self, now_ms: float):
        if self.state in {"final_fade", "cleanup", "done"}:
            return
        for key in ["logo_favo", "logo_favo_view", "logo_favo_view_p1", "logo_favo_view_p2", "logo_favo_view_p3"]:
            self.schedule_alpha(key, None, 0, now_ms, 2500.0, 0)
        self.final_fade_end_ms = now_ms + 2500.0
        self.state = "final_fade"
        self.state_enter_ms = now_ms
        self.hint_var.set("进入统一淡出阶段…")

    def start_quick_cleanup(self, now_ms: float):
        if self.state in {"cleanup", "done"}:
            return
        for key in ["logo_favo_view", "logo_favo_view_p1", "logo_favo_view_p2", "logo_favo_view_p3", "logo_bg", "logo_favo"]:
            self.schedule_alpha(key, None, 0, now_ms, 100.0, 0)
        self.quick_cleanup_end_ms = now_ms + 100.0
        self.state = "cleanup"
        self.state_enter_ms = now_ms
        self.hint_var.set("快速清理图层…")

    def update_state_machine(self, now_ms: float):
        if self.state == "intro":
            if self.skip_requested:
                self.start_final_fade(now_ms)
            elif now_ms >= 1800.0:
                self.start_background_fade(now_ms)
        elif self.state == "post_intro_wait":
            if self.skip_requested or (now_ms - self.state_enter_ms) >= 1200.0:
                self.start_final_fade(now_ms)
        elif self.state == "final_fade":
            if self.skip_requested and (now_ms - self.state_enter_ms) >= 200.0:
                self.start_quick_cleanup(now_ms)
            elif now_ms >= self.final_fade_end_ms:
                self.start_quick_cleanup(now_ms)
        elif self.state == "cleanup":
            if now_ms >= self.quick_cleanup_end_ms + 300.0:
                self.state = "done"
                self.sequence_finished = True
                self.hint_var.set("演出结束。关闭窗口可退出；按 R 重新运行")
                self.root.bind("r", self.restart)
                self.root.bind("R", self.restart)
                if self.auto_close:
                    self.root.after(600, self.root.destroy)

    def restart(self, _event=None):
        self.skip_requested = False
        self.sequence_finished = False
        self.state = "intro"
        self.state_enter_ms = 0.0
        self.final_fade_end_ms = 0.0
        self.quick_cleanup_end_ms = 0.0
        self.started_at = time.perf_counter()
        self.tweens.clear()
        self.layers = build_layers(self.asset_dir)
        self.canvas.delete("all")
        for layer in sorted(self.layers.values(), key=lambda x: x.order):
            layer.canvas_item = self.canvas.create_image(0, 0, anchor="nw")
        self.setup_intro_tweens()
        self.hint_var.set("点击鼠标、空格、回车或 Esc 可跳过")

    def update_tweens(self, now_ms: float):
        for tween in self.tweens:
            layer = self.layers[tween.layer_key]
            tween.apply(now_ms, layer)
        self.tweens = [t for t in self.tweens if not t.finished]

    def render_layer(self, layer: LayerState) -> Image.Image | None:
        if alpha_to_int(layer.alpha) <= 0:
            return None

        depth_scale = compute_depth_scale(layer.z_value) if layer.depth_enabled else 1.0
        sx = max(0.01, (layer.scale_x_factor / FACTOR_DENOM) * depth_scale)
        sy = max(0.01, (layer.scale_y_factor / FACTOR_DENOM) * depth_scale)

        img = layer.image
        new_w = max(1, int(round(img.width * sx)))
        new_h = max(1, int(round(img.height * sy)))
        rendered = img.resize((new_w, new_h), RESAMPLE_LANCZOS)

        if alpha_to_int(layer.alpha) < 255:
            rendered = rendered.copy()
            alpha_channel = rendered.getchannel("A")
            alpha_channel = alpha_channel.point(lambda value: int(value * alpha_to_int(layer.alpha) / 255))
            rendered.putalpha(alpha_channel)

        pivot_world_x = layer.x
        pivot_world_y = layer.y

        pivot_local_x = (layer.pivot_x * sx) if layer.pivot_x > 0 else (rendered.width / 2.0)
        pivot_local_y = (layer.pivot_y * sy) if layer.pivot_y > 0 else (rendered.height / 2.0)
        top_left_x = pivot_world_x - pivot_local_x
        top_left_y = pivot_world_y - pivot_local_y

        frame = Image.new("RGBA", (WINDOW_W, WINDOW_H), (0, 0, 0, 0))
        frame.paste(rendered, (int(round(top_left_x)), int(round(top_left_y))), rendered)

        if abs(layer.rotation_tenths) > 0.01:
            frame = frame.rotate(
                -layer.rotation_tenths / 10.0,
                resample=RESAMPLE_BICUBIC,
                expand=False,
                center=(pivot_world_x, pivot_world_y),
            )

        return frame

    def draw(self):
        for layer in sorted(self.layers.values(), key=lambda x: x.order):
            image = self.render_layer(layer)
            if image is None:
                if layer.canvas_item is not None:
                    self.canvas.itemconfigure(layer.canvas_item, state="hidden")
                continue
            layer.photo = ImageTk.PhotoImage(image)
            if layer.canvas_item is None:
                layer.canvas_item = self.canvas.create_image(0, 0, anchor="nw", image=layer.photo)
            else:
                self.canvas.coords(layer.canvas_item, 0, 0)
                self.canvas.itemconfigure(layer.canvas_item, image=layer.photo, state="normal")
        self.debug_var.set(
            f"assets: {self.asset_dir} | state={self.state} | skip={self.skip_requested} | t={self.elapsed_ms():.0f}ms"
        )

    def tick(self):
        now_ms = self.elapsed_ms()
        self.update_state_machine(now_ms)
        self.update_tweens(now_ms)
        self.draw()
        self.root.after(FRAME_MS, self.tick)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="复现 f_00074DA5 的 LOGO 演出")
    parser.add_argument(
        "--assets",
        type=Path,
        default=DEFAULT_ASSET_DIR,
        help="外置图片目录；默认使用脚本同级的 logo_assets 文件夹",
    )
    parser.add_argument(
        "--auto-close",
        action="store_true",
        help="演出结束后自动关闭窗口",
    )
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    root = tk.Tk()
    LogoSequencePlayer(root, args.assets, auto_close=args.auto_close)
    root.mainloop()


if __name__ == "__main__":
    main()
