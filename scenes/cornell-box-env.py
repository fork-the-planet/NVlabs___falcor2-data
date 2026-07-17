# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import falcor2 as f2
import slangpy as spy
from falcor2 import pyscene


position = spy.float3(0, 1, 4)
target = spy.float3(0, 1, 0)
camera_transform = f2.Transform()
camera_transform.translation = position
camera_transform.rotation = spy.math.quat_from_look_at(
    spy.math.normalize(target - position),
    spy.float3(0, 1, 0),
)


pyscene.nodes.create_camera_fov(name="Camera", transform=camera_transform.matrix)
pyscene.load_asset("../assets/cornell-box/usdpreviewsurface/cornell-box.usda")
pyscene.env.set("../assets/envmaps/aerodynamics_workshop_512.hdr", exposure=5)


if __name__ == "__main__":
    pyscene.preview()
