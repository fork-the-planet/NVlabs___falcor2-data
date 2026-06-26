# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
from typing import Any

import falcor2 as f2
import slangpy as spy
from falcor2.importers import import_scene
from normalmap_texture import (
    DEFAULT_NORMAL_MAP_PATH,
    assign_normalmap_texture_to_plane_materials,
    create_normalmap_texture,
)


SCENE_PATH = Path(__file__).with_name("glb_bottom.glb")
WIDTH = 1600
HEIGHT = 900
FOV_Y = 22.895194
LIGHT_RADIANCE = spy.float3(8000.0, 8000.0, 8000.0)
LIGHT_CUTOFF_ANGLE = 0.53


def _matrix_to_list(matrix: Any) -> list[list[float]]:
    return [[float(matrix[row][col]) for col in range(4)] for row in range(4)]


def _normalize(value: tuple[float, float, float]) -> tuple[float, float, float]:
    length = (value[0] * value[0] + value[1] * value[1] + value[2] * value[2]) ** 0.5
    if length == 0.0:
        raise RuntimeError("Cannot normalize a zero-length vector.")
    return (value[0] / length, value[1] / length, value[2] / length)


def _matrix_column(matrix: Any, column: int) -> tuple[float, float, float]:
    return (float(matrix[0][column]), float(matrix[1][column]), float(matrix[2][column]))


def _matrix_translation(matrix: Any) -> tuple[float, float, float]:
    return (float(matrix[0][3]), float(matrix[1][3]), float(matrix[2][3]))


def create_scene(
    device: spy.Device,
    width: int = WIDTH,
    height: int = HEIGHT,
    normalmap_path: str | Path | None = None,
) -> tuple[f2.Scene, f2.Camera, dict[str, Any]]:
    importer_scene = import_scene(SCENE_PATH.resolve())
    if importer_scene is None:
        raise RuntimeError(f"Failed to load scene: {SCENE_PATH}")
    if len(importer_scene.cameras) == 0:
        raise RuntimeError(f"Scene has no camera: {SCENE_PATH}")

    plane_material_name: str | None = None
    sphere_had_missing_material = False
    for mesh in importer_scene.meshes:
        mesh_name = mesh.name.lower()
        for subgeometry in mesh.subgeometries:
            if "plane" in mesh_name:
                if subgeometry.material_name == "":
                    raise RuntimeError(f"Plane mesh has no material: {SCENE_PATH}")
                plane_material_name = subgeometry.material_name
    if plane_material_name is None:
        raise RuntimeError(f"Scene has no plane material binding: {SCENE_PATH}")

    meshes = list(importer_scene.meshes)
    for mesh_index, mesh in enumerate(meshes):
        mesh_name = mesh.name.lower()
        subgeometries = list(mesh.subgeometries)
        for subgeometry in subgeometries:
            if subgeometry.material_name != "":
                continue
            if "sphere" in mesh_name:
                subgeometry.material_name = "normalmap_default_sphere_standard"
                sphere_had_missing_material = True
            else:
                raise RuntimeError(f"Mesh '{mesh.name}' has no material: {SCENE_PATH}")
        mesh.subgeometries = subgeometries
        meshes[mesh_index] = mesh
    importer_scene.meshes = meshes

    if sphere_had_missing_material:
        sphere_material = f2.ImporterMaterial()
        sphere_material.name = "normalmap_default_sphere_standard"
        sphere_material.params = f2.Properties(
            {
                "_scene_material_type": "StandardMaterial",
                "base_color_factor": spy.float3(0.5, 0.5, 0.5),
                "metallic_factor": 0.0,
                "roughness_factor": 1.0,
                "double_sided": True,
            }
        )
        materials = list(importer_scene.materials)
        materials.append(sphere_material)
        importer_scene.materials = materials

    imported_camera = importer_scene.cameras[0]
    imported_light_count = len(importer_scene.lights)
    scene = f2.Scene.create(device, importer_scene)
    normalmap_source_path = Path(normalmap_path).resolve() if normalmap_path is not None else None
    normalmap_left_label = "OpenGL" if normalmap_path is None else "Orig"
    normalmap_right_label = "DirectX" if normalmap_path is None else "Flipped"
    normal_texture = create_normalmap_texture(
        device,
        source_path=normalmap_source_path,
        left_label=normalmap_left_label,
        right_label=normalmap_right_label,
    )
    plane_material_names, plane_material_types = assign_normalmap_texture_to_plane_materials(
        scene,
        normal_texture,
        SCENE_PATH,
    )
    scene.update()

    sun_entity = None
    for component in scene.components:
        if isinstance(component, f2.DistantLight) and "sun" in component.entity.name.lower():
            sun_entity = component.entity
            break
    if sun_entity is None:
        for entity in scene.entities:
            if entity.name.lower().split("/")[-1] == "sun":
                sun_entity = entity
                break
    if sun_entity is None:
        raise RuntimeError(f"Scene has no Sun entity to derive light direction: {SCENE_PATH}")
    sun_matrix = sun_entity.world_from_object_matrix

    for component in scene.components:
        if isinstance(component, f2.Light):
            component.active = False

    light_entity = scene.create_entity()
    light_entity.name = "Parity Sun"
    light_entity.set_world_transform(f2.Transform(sun_matrix))
    parity_light = light_entity.create_component(f2.DistantLight)
    parity_light.name = "Parity Sun"
    parity_light.radiance = LIGHT_RADIANCE
    parity_light.cutoff_angle = LIGHT_CUTOFF_ANGLE

    sphere_material_names: list[str] = []
    sphere_material_types: list[str] = []
    for component in scene.components:
        if (
            not isinstance(component, f2.GeometryInstance)
            or "sphere" not in component.entity.name.lower()
        ):
            continue
        for material in component.materials:
            sphere_material_names.append(material.name)
            sphere_material_types.append(material.slang_type_name)

    camera = scene.active_camera
    if camera is None:
        camera = scene.components.find(type=f2.Camera)
    if camera is None:
        raise RuntimeError(f"Scene has no runtime camera: {SCENE_PATH}")
    camera.width = width
    camera.height = height
    camera.fov_y = FOV_Y
    camera.recompute()
    scene.active_camera = camera
    scene.update()

    camera_matrix = camera.entity.world_from_object_matrix
    light_matrix = light_entity.world_from_object_matrix
    metadata: dict[str, Any] = {
        "label": "glb_bottom",
        "row": "bottom",
        "format": "glb",
        "scene_path": str(SCENE_PATH),
        "normalmap_source_path": str(
            normalmap_source_path if normalmap_source_path is not None else DEFAULT_NORMAL_MAP_PATH
        ),
        "normalmap_left_label": normalmap_left_label,
        "normalmap_right_label": normalmap_right_label,
        "width": width,
        "height": height,
        "imported_camera_name": imported_camera.name,
        "imported_camera_focal_length": float(imported_camera.focal_length),
        "override_fov_y": FOV_Y,
        "camera_matrix": _matrix_to_list(camera_matrix),
        "camera_position": _matrix_translation(camera_matrix),
        "camera_forward": _normalize(
            (
                -float(camera_matrix[0][2]),
                -float(camera_matrix[1][2]),
                -float(camera_matrix[2][2]),
            )
        ),
        "imported_light_count": imported_light_count,
        "source_sun_entity": sun_entity.name,
        "light_matrix": _matrix_to_list(light_matrix),
        "light_direction": _normalize(_matrix_column(light_matrix, 2)),
        "light_radiance": (8000.0, 8000.0, 8000.0),
        "light_cutoff_angle": LIGHT_CUTOFF_ANGLE,
        "plane_material_names": plane_material_names,
        "plane_material_types": plane_material_types,
        "sphere_material_names": sphere_material_names,
        "sphere_material_types": sphere_material_types,
        "sphere_had_missing_material": sphere_had_missing_material,
    }
    return scene, camera, metadata
