# SPDX-License-Identifier: GPL-2.0-or-later

"""Operadores de arrastre (drag) de las herramientas Modo Move/Rotate/Scale.

Los handles del gizmo (drag restringido a eje) los resuelve el propio gizmo de
Blender (VIEW3D_GGT_xform_gizmo / tools nativos), idéntico a como lo hace
Blender. Estos operadores cubren el clic+arrastre que NO cae sobre un handle:
aplican la transformación restringida al plano del **eje cartesiano dominante**
(el X/Y/Z del mundo más alineado con la dirección de la cámara — "el eje más
enfocado", snap).

- Move  (W): traslada en el plano de los dos ejes cartesianos restantes.
- Rotate(E): rota alrededor del eje dominante (giro en pantalla).
- Scale (R): escala en el plano de los dos ejes restantes.

Cada operador tiene un `kind` y su `poll` exige que `window_manager.
modonize_transform_kind` coincida; así, al arrastrar, sólo el drag de la
herramienta activa entra en juego (los demás fallan el poll y Blender pasa al
siguiente item).

Pivot: mediana de la selección en coordenadas mundiales. LIVE preview durante el
modal y restauración completa al cancelar (ESC / botón derecho).
"""

import mathutils
from bpy_extras import view3d_utils

import bpy

from .. import _state

_AXES = (
    ("X", mathutils.Vector((1.0, 0.0, 0.0))),
    ("Y", mathutils.Vector((0.0, 1.0, 0.0))),
    ("Z", mathutils.Vector((0.0, 0.0, 1.0))),
)


def _enabled(context):
    try:
        return bool(_state.prefs(context).enable_transform)
    except Exception:
        return False


def _kind_matches(context, kind):
    return getattr(context.window_manager, "modonize_transform_kind", "") == kind


class _DragBase:
    """Estado y matemática común de los tres operadores de arrastre."""

    def _collect(self, context):
        """Captura la selección a transformar y el pivot (coords mundiales)."""
        self._mode = context.mode
        if self._mode == "EDIT_MESH":
            obj = context.active_object
            if obj is None or obj.type != "MESH":
                return False
            import bmesh
            bm = bmesh.from_edit_mesh(obj.data)
            verts = [v for v in bm.verts if v.select]
            if not verts:
                return False
            self._edit_obj = obj
            self._edit_verts = verts
            self._edit_start = [v.co.copy() for v in verts]
            pivot = sum((obj.matrix_world @ v.co for v in verts), mathutils.Vector()) / len(verts)
            self._pivot_world = pivot
            self._objects = []
            return True
        if self._mode == "OBJECT":
            objs = list(context.selected_objects)
            if not objs:
                return False
            self._objects = objs
            self._object_start = {o: o.matrix_world.copy() for o in objs}
            pivot = sum((o.matrix_world.translation for o in objs), mathutils.Vector()) / len(objs)
            self._pivot_world = pivot
            self._edit_obj = None
            return True
        return False

    # -- matemática de la vista ---------------------------------------------

    def _dominant_axis(self, context):
        """(nombre, vector dirección mundial) del eje cartesiano dominante."""
        rv3d = context.region_data
        view_dir = -(rv3d.view_rotation @ mathutils.Vector((0.0, 0.0, 1.0)))
        best_name, best_vec, best_abs = "Z", _AXES[2][1], 0.0
        for name, vec in _AXES:
            d = view_dir.dot(vec)
            if abs(d) > best_abs:
                best_abs, best_name, best_vec = abs(d), name, vec
        if view_dir.dot(best_vec) < 0:
            best_vec = -best_vec
        return best_name, best_vec

    def _plane_basis(self, context, dom_vec):
        """Bases ortonormales u,v (mundo) del plano perpendicular a dom_vec."""
        rv3d = context.region_data
        right = rv3d.view_rotation @ mathutils.Vector((1.0, 0.0, 0.0))
        up = rv3d.view_rotation @ mathutils.Vector((0.0, 1.0, 0.0))
        u = right - dom_vec * right.dot(dom_vec)
        v = up - dom_vec * up.dot(dom_vec)
        for w in (u, v):
            if w.length > 1e-6:
                w.normalize()
        if u.length_squared < 1e-6 or v.length_squared < 1e-6 or abs(u.dot(v)) > 0.99:
            for _, vec in _AXES:
                if abs(dom_vec.dot(vec)) < 0.99:
                    if u.length_squared < 1e-6:
                        u = vec.copy()
                    elif abs(u.dot(vec)) < 0.99:
                        v = vec.copy()
                        break
            u.normalize()
            v.normalize()
        if abs(u.dot(v)) > 0.99:
            v = dom_vec.cross(u)
            v.normalize()
        return u, v

    def _region(self, context):
        return context.region, context.region_data

    def _delta_world(self, context, event):
        """Desplazamiento mundial del ratón proyectado al plano del eje dominante."""
        region, rv3d = self._region(context)
        cur = view3d_utils.region_2d_to_location_3d(
            region, rv3d, (event.mouse_region_x, event.mouse_region_y), self._pivot_world
        )
        start = view3d_utils.region_2d_to_location_3d(
            region, rv3d, self._start_mouse, self._pivot_world
        )
        _, dom_vec = self._dominant_axis(context)
        u, v = self._plane_basis(context, dom_vec)
        d = cur - start
        return d.dot(u) * u + d.dot(v) * v

    def _pivot_screen(self, context):
        region, rv3d = self._region(context)
        p = view3d_utils.location_3d_to_region_2d(region, rv3d, self._pivot_world)
        return p if p is not None else mathutils.Vector((0.0, 0.0))

    # -- aplicación ----------------------------------------------------------

    def _apply_edit(self, world_func):
        inv = self._edit_obj.matrix_world.inverted()
        for i, v in enumerate(self._edit_verts):
            start_world = self._edit_obj.matrix_world @ self._edit_start[i]
            v.co = inv @ world_func(start_world)
        bmesh.update_edit_mesh(self._edit_obj.data)

    def _apply_objects(self, world_func):
        for o in self._objects:
            o.matrix_world = world_func(self._object_start[o])

    def _apply(self, world_func):
        if self._edit_obj is not None:
            self._apply_edit(world_func)
        else:
            self._apply_objects(world_func)

    def _restore(self):
        if self._edit_obj is not None:
            for i, v in enumerate(self._edit_verts):
                v.co = self._edit_start[i]
            bmesh.update_edit_mesh(self._edit_obj.data)
        for o in self._objects:
            o.matrix_world = self._object_start[o]

    def _cancel(self, context):
        self._restore()
        context.area.header_text_set(None)
        return {"CANCELLED"}

    def _finish(self, context):
        context.area.header_text_set(None)
        return {"FINISHED"}

    def _escape_or_cancel(self, context, event):
        return (
            (event.type == "ESC" and event.value == "PRESS")
            or (event.type == "RIGHTMOUSE" and event.value == "PRESS")
        )


class MODOZ_OT_DragMove(bpy.types.Operator, _DragBase):
    bl_idname = "modoz.drag_move"
    bl_label = "Mover en el plano del eje dominante"
    bl_description = (
        "Arrastra la selección en el plano de los dos ejes cartesianos "
        "perpendiculares al eje dominante de la cámara."
    )
    bl_options = {"REGISTER", "UNDO"}
    kind = "move"

    @classmethod
    def poll(cls, context):
        return _enabled(context) and context.mode in ("OBJECT", "EDIT_MESH") and _kind_matches(context, cls.kind)

    def invoke(self, context, event):
        if not self._collect(context):
            return {"CANCELLED"}
        self._start_mouse = (event.mouse_region_x, event.mouse_region_y)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if self._escape_or_cancel(context, event):
            return self._cancel(context)
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            return self._finish(context)
        if event.type == "MOUSEMOVE":
            dom_name, _ = self._dominant_axis(context)
            shift = self._delta_world(context, event)
            self._apply(lambda w: w + shift)
            context.area.header_text_set(
                f"Move [{dom_name}]: {shift.x:.3f}, {shift.y:.3f}, {shift.z:.3f}"
            )
        return {"RUNNING_MODAL"}


class MODOZ_OT_DragRotate(bpy.types.Operator, _DragBase):
    bl_idname = "modoz.drag_rotate"
    bl_label = "Rotar alrededor del eje dominante"
    bl_description = (
        "Rota la selección alrededor del eje cartesiano dominante de la cámara "
        "(giro en pantalla alrededor del pivot)."
    )
    bl_options = {"REGISTER", "UNDO"}
    kind = "rotate"

    @classmethod
    def poll(cls, context):
        return _enabled(context) and context.mode in ("OBJECT", "EDIT_MESH") and _kind_matches(context, cls.kind)

    def invoke(self, context, event):
        if not self._collect(context):
            return {"CANCELLED"}
        self._start_mouse = (event.mouse_region_x, event.mouse_region_y)
        self._pivot_scr = self._pivot_screen(context)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if self._escape_or_cancel(context, event):
            return self._cancel(context)
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            return self._finish(context)
        if event.type == "MOUSEMOVE":
            dom_name, dom_vec = self._dominant_axis(context)
            cur = mathutils.Vector((event.mouse_region_x, event.mouse_region_y))
            start = mathutils.Vector(self._start_mouse)
            base = cur - self._pivot_scr
            ref = start - self._pivot_scr
            angle = base.angle_signed(ref) if base.length > 1e-6 else 0.0
            M = (
                mathutils.Matrix.Translation(self._pivot_world)
                @ mathutils.Matrix.Rotation(angle, 4, dom_vec)
                @ mathutils.Matrix.Translation(-self._pivot_world)
            )
            self._apply(lambda w: M @ w)
            context.area.header_text_set(f"Rotate [{dom_name}]: {angle * 57.2958:.1f}°")
        return {"RUNNING_MODAL"}


class MODOZ_OT_DragScale(bpy.types.Operator, _DragBase):
    bl_idname = "modoz.drag_scale"
    bl_label = "Escalar en el plano del eje dominante"
    bl_description = (
        "Escala la selección en el plano de los dos ejes cartesianos "
        "perpendiculares al eje dominante de la cámara (anisotrópico)."
    )
    bl_options = {"REGISTER", "UNDO"}
    kind = "scale"

    @classmethod
    def poll(cls, context):
        return _enabled(context) and context.mode in ("OBJECT", "EDIT_MESH") and _kind_matches(context, cls.kind)

    def invoke(self, context, event):
        if not self._collect(context):
            return {"CANCELLED"}
        self._start_mouse = (event.mouse_region_x, event.mouse_region_y)
        self._pivot_scr = self._pivot_screen(context)
        d = mathutils.Vector(self._start_mouse) - self._pivot_scr
        self._start_dist = max(d.length, 1e-3)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if self._escape_or_cancel(context, event):
            return self._cancel(context)
        if event.type == "LEFTMOUSE" and event.value == "RELEASE":
            return self._finish(context)
        if event.type == "MOUSEMOVE":
            dom_name, dom_vec = self._dominant_axis(context)
            u, v = self._plane_basis(context, dom_vec)
            cur = mathutils.Vector((event.mouse_region_x, event.mouse_region_y))
            t = max((cur - self._pivot_scr).length / self._start_dist, 1e-4)
            A = mathutils.Matrix().to_3x3()
            A[0][0], A[1][0], A[2][0] = u * t
            A[0][1], A[1][1], A[2][1] = v * t
            A[0][2], A[1][2], A[2][2] = dom_vec
            M = (
                mathutils.Matrix.Translation(self._pivot_world)
                @ A.to_4x4()
                @ mathutils.Matrix.Translation(-self._pivot_world)
            )
            self._apply(lambda w: M @ w)
            context.area.header_text_set(f"Scale [{dom_name}]: {t:.3f}")
        return {"RUNNING_MODAL"}


_CLASSES = (
    MODOZ_OT_DragMove,
    MODOZ_OT_DragRotate,
    MODOZ_OT_DragScale,
)


def register():
    from .. import _state as _s
    for cls in _CLASSES:
        _s.register_class_safe(cls)


def unregister():
    from .. import _state as _s
    for cls in reversed(_CLASSES):
        _s.unregister_class_safe(cls)