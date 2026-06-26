# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Union

import numpy as np
import slangpy as spy

from normalmap_glyphs import GLYPHS


DEFAULT_NORMAL_MAP_PATH = Path(__file__).with_name("Normal_Plane.png")
DEFAULT_LEFT_LABEL = "Orig"
DEFAULT_RIGHT_LABEL = "Flip"
SCRIPT_LEFT_LABEL = "OpenGL"
SCRIPT_RIGHT_LABEL = "DirectX"

PathLike = Union[str, os.PathLike]


def resolve_labels(
    left_label: str | None = None,
    right_label: str | None = None,
) -> tuple[str, str]:
    return (
        DEFAULT_LEFT_LABEL if left_label is None else left_label,
        DEFAULT_RIGHT_LABEL if right_label is None else right_label,
    )


def _load_normal_map_pixels(source: Path) -> np.ndarray:
    bitmap = spy.Bitmap.load_from_file(str(source)).convert(
        pixel_format=spy.Bitmap.PixelFormat.rgba,
        component_type=spy.Bitmap.ComponentType.float32,
        srgb_gamma=True,
    )
    return np.array(bitmap, dtype=np.float32, copy=True)


def _text_size(label: str, scale: int) -> tuple[int, int]:
    if label == "":
        return (0, 0)
    glyph_width = 5 * scale
    spacing = scale
    return (len(label) * glyph_width + (len(label) - 1) * spacing, 7 * scale)


def _draw_glyph(
    pixels: np.ndarray,
    glyph: tuple[str, ...],
    x: int,
    y: int,
    scale: int,
    color: tuple[float, float, float, float],
) -> None:
    height, width, _ = pixels.shape
    for row, bits in enumerate(glyph):
        for col, bit in enumerate(bits):
            if bit != "1":
                continue
            x0 = max(0, x + col * scale)
            y0 = max(0, y + row * scale)
            x1 = min(width, x0 + scale)
            y1 = min(height, y0 + scale)
            if x0 < x1 and y0 < y1:
                pixels[y0:y1, x0:x1, :] = color


def _draw_text(
    pixels: np.ndarray,
    label: str,
    x: int,
    y: int,
    scale: int,
    color: tuple[float, float, float, float],
) -> None:
    cursor_x = x
    for char in label.upper():
        _draw_glyph(pixels, GLYPHS.get(char, GLYPHS["?"]), cursor_x, y, scale, color)
        cursor_x += 6 * scale


def _draw_centered_label(
    pixels: np.ndarray,
    label: str,
    x0: int,
    y_center: int,
    width: int,
) -> None:
    if label == "":
        return
    height = pixels.shape[0]
    scale = max(1, round(height * 0.012))
    text_width, text_height = _text_size(label, scale)
    text_x = round(x0 + (width - text_width) * 0.5)
    text_y = round(y_center - text_height * 0.5)
    stroke = max(1, round(scale * 0.18))
    stroke_color = (0.05, 0.05, 0.08, 1.0)
    text_color = (1.0, 1.0, 1.0, 1.0)
    for offset_x, offset_y in ((-stroke, 0), (stroke, 0), (0, -stroke), (0, stroke)):
        _draw_text(pixels, label, text_x + offset_x, text_y + offset_y, scale, stroke_color)
    _draw_text(pixels, label, text_x, text_y, scale, text_color)


def make_normalmap_comparison(
    source_path: PathLike | None = None,
    left_label: str | None = None,
    right_label: str | None = None,
    overlay_labels: bool = True,
) -> np.ndarray:
    source = Path(source_path) if source_path is not None else DEFAULT_NORMAL_MAP_PATH
    if not source.exists():
        raise FileNotFoundError(f"Normal map source does not exist: {source}")

    source_pixels = _load_normal_map_pixels(source)
    flipped_pixels = source_pixels.copy()
    flipped_pixels[..., 1] = 1.0 - flipped_pixels[..., 1]
    combined_pixels = np.concatenate([source_pixels, flipped_pixels], axis=1)

    if not overlay_labels:
        return np.ascontiguousarray(combined_pixels, dtype=np.float32)

    labels = resolve_labels(left_label, right_label)
    labeled_pixels = combined_pixels.copy()
    half_width = source_pixels.shape[1]
    label_y = round(source_pixels.shape[0] * 0.43)
    _draw_centered_label(labeled_pixels, labels[0], 0, label_y, half_width)
    _draw_centered_label(labeled_pixels, labels[1], half_width, label_y, half_width)
    return np.ascontiguousarray(labeled_pixels, dtype=np.float32)


def create_normalmap_texture(
    device: Any,
    source_path: PathLike | None = None,
    left_label: str | None = None,
    right_label: str | None = None,
) -> Any:
    pixels = make_normalmap_comparison(
        source_path=source_path,
        left_label=left_label,
        right_label=right_label,
    )
    height, width, _ = pixels.shape
    return device.create_texture(
        type=spy.TextureType.texture_2d,
        format=spy.Format.rgba32_float,
        width=width,
        height=height,
        mip_count=1,
        usage=spy.TextureUsage.shader_resource,
        data=np.ascontiguousarray(pixels.reshape((-1, 4))),
    )


def assign_normalmap_texture_to_plane_materials(
    scene: Any,
    normal_texture: Any,
    scene_path: PathLike,
) -> tuple[list[str], list[str]]:
    import falcor2 as f2

    plane_material_names: list[str] = []
    plane_material_types: list[str] = []
    plane_found = False
    for component in scene.components:
        if (
            not isinstance(component, f2.GeometryInstance)
            or "plane" not in component.entity.name.lower()
        ):
            continue
        plane_found = True
        for material in component.materials:
            if material.slang_type_name != "StandardMaterial":
                raise RuntimeError(
                    f"Plane material '{material.name}' converted to "
                    f"'{material.slang_type_name}', expected StandardMaterial."
                )
            material["normal_texture"] = normal_texture
            material["normal_texture_scale"] = 1.0
            plane_material_names.append(material.name)
            plane_material_types.append(material.slang_type_name)
    if not plane_found:
        raise RuntimeError(f"Scene has no plane geometry instance: {scene_path}")
    return plane_material_names, plane_material_types


def save_normalmap_comparison(
    output_path: PathLike,
    source_path: PathLike | None = None,
    left_label: str | None = SCRIPT_LEFT_LABEL,
    right_label: str | None = SCRIPT_RIGHT_LABEL,
) -> None:
    pixels = make_normalmap_comparison(
        source_path=source_path,
        left_label=left_label,
        right_label=right_label,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    bitmap = spy.Bitmap(
        data=np.clip(pixels, 0.0, 1.0),
        pixel_format=spy.Bitmap.PixelFormat.rgba,
        srgb_gamma=True,
    ).convert(
        component_type=spy.Bitmap.ComponentType.uint8,
        srgb_gamma=True,
    )
    bitmap.write(str(output), spy.Bitmap.FileFormat.png)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a normal-map comparison texture.")
    parser.add_argument(
        "output",
        nargs="?",
        default="normalmap_comparison.png",
        help="Output PNG path.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_NORMAL_MAP_PATH,
        help="Source normal map path.",
    )
    parser.add_argument("--left-label", default=SCRIPT_LEFT_LABEL)
    parser.add_argument("--right-label", default=SCRIPT_RIGHT_LABEL)
    args = parser.parse_args(argv)

    save_normalmap_comparison(
        output_path=args.output,
        source_path=args.source,
        left_label=args.left_label,
        right_label=args.right_label,
    )
    print(Path(args.output).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
