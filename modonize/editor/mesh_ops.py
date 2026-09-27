# SPDX-License-Identifier: GPL-2.0-or-later

"""Operadores auxiliares de edición de malla (usados por las teclas [B], [L], etc.)."""

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


class ModozBevel(bpy.types.Operator):
    bl_idname = "modoz.bevel"
    bl_label = "Bevel (Modonize)"
    bl_description = (
        "Lanza la herramienta nativa de Blender según el modo de selección: "
        "bevel (vértices o aristas) según el modo, o extrude sobre las "
        "normales en modo polígono."
    )
    # Sin REGISTER y sin propiedades propias: el redo panel (F9) y el modal
    # los pone el operador nativo invocado (bevel o extrude), que es el que
    # entra en la pila de undo/redo.
    bl_options = set()

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"

    def execute(self, context):
        mode = _state.current_component_mode(context)
        if mode == "FACE":
            # Modo polígono: comando nativo "Extrude Along Normals".
            return self._extrude_along_normals(context)

        # Modos vértice y arista: bevel nativo de Blender con su configuración
        # (afectar a vértices o aristas), lanzado en modo modal (INVOKE_DEFAULT)
        # igual que el Ctrl+B de serie: arrastras para ajustar y confirmas con
        # clic. El F9 del propio bevel ofrece luego "Afectar a: Vértices/
        # Aristas", "Segmentos", etc.
        affect = "VERTICES" if mode == "VERT" else "EDGES"
        try:
            bpy.ops.mesh.bevel("INVOKE_DEFAULT", affect=affect)
        except Exception:
            # Blender < 3.2: bevel sin 'affect' (infiere del modo visual).
            bpy.ops.mesh.bevel("INVOKE_DEFAULT")
        return {"FINISHED"}

    def _extrude_along_normals(self, context):
        # Comando nativo "Extrude Along Normals" (Alt+E): extrude de región
        # unida + arrastre modal a lo largo de las normales.
        bpy.ops.mesh.extrude_region_shrink_fatten("INVOKE_DEFAULT")
        return {"FINISHED"}


_CLASSES = (ModozSelectLoop, ModozBevel)


def register():
    for cls in _CLASSES:
        _state.register_class_safe(cls)


def unregister():
    for cls in reversed(_CLASSES):
        _state.unregister_class_safe(cls)