# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from falcor2 import pyscene


pyscene.load_asset("../assets/cornell-box/usdpreviewsurface/cornell-box.usda")


if __name__ == "__main__":
    pyscene.preview()
