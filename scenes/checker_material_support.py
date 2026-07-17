# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

import falcor2 as f2
import slangpy as spy
from falcor2.reflection import Property


SLANG_SOURCE_PATH = Path(__file__).resolve().parent / "shaders" / "checker_material.slang"


class CheckerMaterial(f2.Material):
    color_a = Property(
        spy.float3(0.92, 0.62, 0.24),
        doc="First checker color",
        on_change=lambda self: self.mark_dirty(f2.Material.DirtyFlags.properties),
    )
    color_b = Property(
        spy.float3(0.10, 0.18, 0.35),
        doc="Second checker color",
        on_change=lambda self: self.mark_dirty(f2.Material.DirtyFlags.properties),
    )
    scale = Property(
        12.0,
        doc="Checker frequency in UV space",
        value_range=(1.0, 128.0),
        on_change=lambda self: self.mark_dirty(f2.Material.DirtyFlags.properties),
    )

    def __init__(self) -> None:
        super().__init__()
        self.slang_type_name = "CheckerMaterial"
        self._module: spy.SlangModule | None = None

    def update(self, ctx: f2.SceneUpdateContext) -> None:
        if self._module is None:
            source = SLANG_SOURCE_PATH.read_text(encoding="ascii")
            self._module = self.scene.device.load_module_from_source("checker_material", source)

    def write_to_cursor(self, cursor: spy.BufferElementCursor | spy.ShaderCursor) -> None:
        cursor["color_a"] = self.color_a
        cursor["color_b"] = self.color_b
        cursor["scale"] = self.scale

    def required_module(self) -> spy.SlangModule | None:
        return self._module

    def get_this(self) -> dict[str, Any]:
        return {
            "color_a": self.color_a,
            "color_b": self.color_b,
            "scale": self.scale,
            "_type": self.slang_type_name,
        }
