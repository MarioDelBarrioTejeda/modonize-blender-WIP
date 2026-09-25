# SPDX-License-Identifier: GPL-2.0-or-later

"""Overlay del gizmo Modo (via draw_handler de SpaceView3D).

En vez de depender del sistema de herramientas/barra (frágil y no verificable),
se pinta una insignia de transformación directamente en el viewport: tres
flechas de ejes (X/Y/Z) o un anillo, centradas en la mediana de la selección,
según la herramienta Modo activa en `window_manager.modonize_transform_kind`.

Al ser un draw_handler de `SpaceView3D`, se redibuja cada frame y no necesita
que una herramienta esté registrada en la barra ni el sistema de gizmos de
Blender.
"""

import bpy
import gpu
import blf
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils
from mathutils import Vector

# (idname_alias para mantener compatibilidad con el resto del addon)
_WIDGETS = {"move", "rotate", "scale"}

_COLORS = {
    "X": (0.9, 0.25, 0.25, 1.0),
    "Y": (0.35, 0.85, 0.35, 1.0),
    "Z": (0.3, 0.5, 1.0, 1.0),
    "label": (1.0, 1.0, 1.0, 1.0),
}

_handle = None


def _kind(context):
    return getattr(context.window_manager, "modonize_transform_kind", "")


def _median(context):
    mode = context.mode
    if mode == "EDIT_MESH":
        obj = context.active_object
        if obj is None or obj.type != "MESH":
            return None
        import bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        sel = [v for v in bm.verts if v.select]
        if not sel:
            return None
        acc = Vector()
        for v in sel:
            acc += obj.matrix_world @ v.co
        return acc / len(sel)
    if mode == "OBJECT":
        sel = [o for o in context.selected_objects]
        if not sel:
            return None
        acc = Vector()
        for o in sel:
            acc += o.matrix_world.translation
        return acc / len(sel)
    return None


def _project(region, rv3d, world):
    p = view3d_utils.location_3d_to_region_2d(region, rv3d, world)
    return (p.x, p.y) if p is not None else None


def _draw_axes(region, rv3d, pivot, size):
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    gpu.state.line_width_set(3.0)
    axes = {
        "X": Vector((1, 0, 0)),
        "Y": Vector((0, 1, 0)),
        "Z": Vector((0, 0, 1)),
    }
    for name, vec in axes.items():
        p0 = _project(region, rv3d, pivot)
        p1 = _project(region, rv3d, pivot + vec * size)
        if p0 is None or p1 is None:
            continue
        # línea del eje
        batch = batch_for_shader(
            shader, "LINES", {"pos": [p0, p1]}, indices=[(0, 1)]
        )
        shader.bind()
        shader.uniform_float("color", _COLORS[name])
        batch.draw(shader)
        # flecha: dos líneas del vértice hacia atrás
        v = (p1[0] - p0[0], p1[1] - p0[1])
        ln = (v[0] * v[0] + v[1] * v[1]) ** 0.5 or 1.0
        w = (-v[1] / ln, v[0] / ln)
        h = 7.0
        bx = (p1[0] - v[0] / ln * h, p1[1] - v[1] / ln * h)
        head = [p1, (bx[0] + w[0] * 5, bx[1] + w[1] * 5), (bx[0] - w[0] * 5, bx[1] - w[1] * 5), p1]
        batch = batch_for_shader(shader, "LINE_STRIP", {"pos": head})
        shader.bind()
        shader.uniform_float("color", _COLORS[name])
        batch.draw(shader)
    gpu.state.line_width_set(1.0)
    gpu.state.blend_set("NONE")


def _draw_ring(region, rv3d, pivot, size):
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    gpu.state.line_width_set(3.0)
    import math
    pts = []
    for i in range(65):
        a = math.radians(i * 360 / 64)
        pts.append(_project(region, rv3d, pivot + Vector((math.cos(a), math.sin(a), 0)) * size))
    pts = [p for p in pts if p is not None]
    if len(pts) > 2:
        batch = batch_for_shader(shader, "LINE_STRIP", {"pos": pts})
        shader.bind()
        shader.uniform_float("color", (1.0, 0.75, 0.3, 0.9))
        batch.draw(shader)
    gpu.state.line_width_set(1.0)
    gpu.state.blend_set("NONE")


def _draw_callback():
    import bpy as _b
    context = _b.context
    kind = _kind(context)
    if kind not in _WIDGETS:
        return
    region = context.region
    rv3d = context.region_data
    if region is None or rv3d is None:
        return
    pivot = _median(context)
    if pivot is None:
        return
    # tamaño del gizmo proporcional a la distancia de vista
    import math
    fov = rv3d.view_perspective
    size = max(rv3d.view_distance * 0.15, 0.1)
    if kind == "rotate":
        _draw_ring(region, rv3d, pivot, size)
    else:
        _draw_axes(region, rv3d, pivot, size)


def register():
    global _handle
    if _handle is None:
        _handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_callback, (), "WINDOW", "POST_PIXEL"
        )


def unregister():
    global _handle
    if _handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_handle, "WINDOW")
        except Exception:
            pass
        _handle = None