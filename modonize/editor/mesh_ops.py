# SPDX-License-Identifier: GPL-2.0-or-later

"""Operadores auxiliares de edición de malla (usados por las teclas [L], etc.)."""

import bpy

from .. import _state


class ModozSelectLoop(bpy.types.Operator):
    bl_idname = "modoz.select_loop"
    bl_label = "Seleccionar loop de aristas"
    bl_description = "Selecciona el edge loop alrededor de la arista activa."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"

    def execute(self, context):
        try:
            if hasattr(bpy.ops.mesh, "select_edge_loop_multi"):
                bpy.ops.mesh.select_edge_loop_multi()
            else:
                bpy.ops.mesh.loop_multi_select(ring=False)
            return {"FINISHED"}
        except Exception:
            return {"CANCELLED"}


_CLASSES = (ModozSelectLoop,)


def register():
    for cls in _CLASSES:
        _state.register_class_safe(cls)


def unregister():
    for cls in reversed(_CLASSES):
        _state.unregister_class_safe(cls)