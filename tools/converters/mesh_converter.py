# 3d, stl, obj, ply, glb, 3mf, mesh, converter

from pathlib import Path
from typing import Literal
import trimesh


def mesh_converter(model: Path, output: Literal["stl", "obj", "ply", "glb", "3mf", "off", "info_only"] = "stl") -> dict:
    """Convert a 3D mesh between STL, OBJ, PLY, GLB/glTF, 3MF and OFF, and report its
    size, volume, surface area, triangle count and whether it is watertight (3D-print
    ready).
    """
    try:
        loaded = trimesh.load(str(model), force="mesh")
    except Exception as e:  # noqa: BLE001
        return {"error": f"Could not read the model: {e}"}
    mesh = loaded if isinstance(loaded, trimesh.Trimesh) else trimesh.util.concatenate(tuple(loaded.geometry.values()))
    extent = mesh.bounding_box.extents
    info = {
        "triangles": int(len(mesh.faces)),
        "vertices": int(len(mesh.vertices)),
        "size_xyz": [round(float(v), 3) for v in extent],
        "watertight": bool(mesh.is_watertight),
        "volume": round(float(mesh.volume), 3) if mesh.is_watertight else "n/a (not watertight)",
        "surface_area": round(float(mesh.area), 3),
        "center_of_mass": [round(float(v), 3) for v in mesh.center_mass] if mesh.is_watertight else "n/a",
    }
    if output == "info_only":
        return info
    out = model.with_suffix("." + output)
    mesh.export(str(out))
    info["file"] = out
    return info
