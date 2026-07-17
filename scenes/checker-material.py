# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import sys
from pathlib import Path

import falcor2 as f2
import slangpy as spy
from falcor2 import pyscene


SCENE_DIR = Path(__file__).resolve().parent
if str(SCENE_DIR) not in sys.path:
    sys.path.insert(0, str(SCENE_DIR))

from checker_material_support import CheckerMaterial  # noqa: E402


position = spy.float3(0, 0, 4)
camera_transform = f2.Transform()
camera_transform.translation = position
camera_transform.rotation = spy.math.quat_from_look_at(
    -spy.math.normalize(position),
    spy.float3(0, 1, 0),
)
pyscene.nodes.create_camera_fov(name="Camera", transform=camera_transform.matrix, fov_degrees=45)
pyscene.load_asset("../assets/kronos/DamagedHelmet/glTF/DamagedHelmet.gltf")
pyscene.env.set("../assets/envmaps/aerodynamics_workshop_512.hdr")

checker_props = f2.Properties()
checker_props["color_a"] = spy.float3(0.92, 0.62, 0.24)
checker_props["color_b"] = spy.float3(0.10, 0.18, 0.35)
checker_props["scale"] = 12.0
pyscene.materials["Material_MR"].replace(CheckerMaterial, checker_props)


if __name__ == "__main__":
    pyscene.preview()
