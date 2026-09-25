# SPDX-License-Identifier: GPL-2.0-or-later

"""GizmoGroup propio de las herramientas Modo Move/Rotate/Scale.

El gizmo nativo de transformación sólo se asocia a los operadores estándar
(`transform.translate/rotate/resize`), por eso no aparece para nuestras
herramientas. Aquí se dibuja un gizmo propio con los **widgets nativos**
(`GIZMO_GT_move_3d`/`rotate_3d`/`resize_3d`), que renderizan el aspecto
estándar (flechas/anillo/recuadros) y disparan nuestros operadores de arrastre.

La herramienta activa la comunica `modoz.set_transform_tool` vía la propiedad
de WindowManager `modonize_transform` (cada herramienta escribe su estado), y
el gizmo se dibuja según ese valor centrado en la mediana de la selección.
"""

import bpy
from mathutils import Matrix, Vector

from .. import _state

# Widgets nativos por tipo de herramienta.
_WIDGETS = {
    "move": "GIZMO_GT_move_3d",
    "rotate": "GIZMO_GT_rotate_3d",
    "scale": "GIZMO_GT_resize_3d",
}


def _kind_from_idname(active):
    if not active.startswith("MODOZ."):
        return ""
    kind = active.split(".", 1)[1].split("_", 1)[0]  # 'MODOZ.move_edit' -> 'move'
    return kind if kind in _WIDGETS else ""


def _kind(context):
    """Tipo de herramienta Modo activa ('move'/'rotate'/'scale') o ''.

    Se deriva de la **herramienta activa** (`context.workspace.tools[0]`) en vez
    de una propiedad propia, para que el gizmo aparezca tanto al pulsar W/E/R
    como al seleccionar la herramienta en la barra de herramientas.
    """
    try:
        tools = context.workspace.tools
        active = tools[0].idname if len(tools) else ""
    except Exception:
        return ""
    return _kind_from_idname(active)


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
        m = obj.matrix_world
        acc = Vector()
        for v in sel:
            acc += m @ v.co
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


class ModonizeTransformGizmoGroup(bpy.types.GizmoGroup):
    bl_idname = "MODOZ_GGT_transform"
    bl_label = "Modo Transform gizmo"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D", "SELECT"}

    @classmethod
    def poll(cls, context):
        prefs = _state.prefs(context)
        if not prefs.enable_transform:
            return False
        return _kind(context) in _WIDGETS and context.mode in ("OBJECT", "EDIT_MESH")

    def setup(self, context):
        self._gizmo = None
        widget = _WIDGETS.get(_kind(context))
        if widget is None:
            return
        g = self.gizmos.new(widget)
        # Espacio mundo: sin esto los widget 3D no pueden situarse/orientarse.
        g.matrix_space = Matrix()
        g.line_width = 2.0
        kind = _kind(context)
        if kind == "move":
            g.color = (0.4, 1.0, 0.4)
            g.color_highlight = (0.8, 1.0, 0.8)
        elif kind == "rotate":
            g.color = (1.0, 0.6, 0.2)
            g.color_highlight = (1.0, 0.85, 0.5)
        else:
            g.color = (0.4, 0.6, 1.0)
            g.color_highlight = (0.7, 0.85, 1.0)
        g.alpha = 0.9
        if hasattr(g, "length"):
            g.length = 1.0
        g.target_set_operator(f"modoz.drag_{kind}")
        self._gizmo = g

    def draw_prepare(self, context):
        pivot = _median(context)
        if pivot is None or self._gizmo is None:
            if self._gizmo is not None:
                self._gizmo.hide = True
            return
        self._gizmo.matrix_space = Matrix()
        self._gizmo.matrix_basis = Matrix.Translation(pivot)
        self._gizmo.hide = False


def register():
    _state.register_class_safe(ModonizeSetTransformTool)
    _state.register_class_safe(ModonizeTransformGizmoGroup)
    if not hasattr(bpy.types.WindowManager, "modonize_transform_kind"):
        bpy.types.WindowManager.modonize_transform_kind = bpy.props.StringProperty(default="")


def unregister():
    _state.unregister_class_safe(ModonizeTransformGizmoGroup)
    _state.unregister_class_safe(ModonizeSetTransformTool)
    if hasattr(bpy.types.WindowManager, "modonize_transform_kind"):
        del bpy.types.WindowManager.modonize_transform_kind


class ModonizeSetTransformTool(bpy.types.Operator):
    bl_idname = "modoz.set_transform_tool"
    bl_label = "Seleccionar herramienta Modo de transformación"
    kind: bpy.props.StringProperty(default="move")
    mode: bpy.props.StringProperty(default="OBJECT")

    def execute(self, context):
        # `kind` gobierna el overlay/drag; además se activa el tool nativo
        # correspondiente (gizmo + pivot/orientaciones/snap de Blender).
        context.window_manager.modonize_transform_kind = self.kind
        for sc in bpy.data.screens:
            for a in sc.areas:
                if a.type == "VIEW_3D":
                    a.tag_redraw()
        builtin = {"move": "builtin.move", "rotate": "builtin.rotate", "scale": "builtin.scale"}.get(self.kind)
        if builtin:
            try:
                bpy.ops.wm.tool_set_by_id(name=builtin)
            except Exception:
                pass
        return {"FINISHED"}