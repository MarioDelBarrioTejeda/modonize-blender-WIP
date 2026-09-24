# SPDX-License-Identifier: GPL-2.0-or-later

"""Operador de doble clic en Edit Mode.

Comportamiento (decisión por defecto sobre las líneas 15/17/19 de la spec):
- Modo Vértices: doble clic -> selecciona toda la malla unida (select_linked).
- Modo Aristas:   doble clic -> selecciona el edge loop (loop_multi_select).
                  doble clic con [Alt] -> selecciona la malla unida.
- Modo Caras:     doble clic -> selecciona la región conectada (select_linked).
"""

import bpy

from .. import _state


class ModozSelectDoubleClick(bpy.types.Operator):
    bl_idname = "modoz.select_double_click"
    bl_label = "Doble clic (selección Modo)"
    bl_options = {"REGISTER", "UNDO"}

    # Por defecto sin modificador; `invoke` lo establece. Debe existir como
    # atributo de clase para que `execute` nunca falle al leerlo aunque el
    # operador se ejecute sin pasar por `invoke` (p. ej. bpy.ops directo).
    _alt = False

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"

    def invoke(self, context, event):
        self._alt = bool(event.alt)
        return self.execute(context)

    def execute(self, context):
        ts = context.tool_settings
        sel = ts.mesh_select_mode
        mode = "VERT" if sel[0] else "EDGE" if sel[1] else "FACE" if sel[2] else None
        if mode is None:
            return {"CANCELLED"}

        prefs = _state.prefs(context)

        # Doble clic con [Alt]: siempre seleccionar malla/región unida.
        if self._alt:
            return self._select_linked(context)

        if mode == "EDGE":
            if prefs.edge_dbl_click == "LOOP":
                return self._select_loop(context)
            return self._select_linked(context)

        if mode in ("VERT", "FACE"):
            return self._select_linked(context)

        return {"CANCELLED"}

    def _select_loop(self, context):
        # El operador de edge loop se renombró entre 4.x (`loop_multi_select`)
        # y 5.2 (`select_edge_loop_multi`). Se selecciona el disponible.
        try:
            if hasattr(bpy.ops.mesh, "select_edge_loop_multi"):
                bpy.ops.mesh.select_edge_loop_multi()
            else:
                bpy.ops.mesh.loop_multi_select(ring=False)
            return {"FINISHED"}
        except Exception:
            return {"CANCELLED"}

    def _select_linked(self, context):
        # Blender colapsa la selección al primer clic; select_linked expande
        # desde el elemento recién seleccionado hacia toda la geometría unida.
        try:
            bpy.ops.mesh.select_linked(delimit=set())
            return {"FINISHED"}
        except RuntimeError:
            return {"CANCELLED"}


def register():
    bpy.utils.register_class(ModozSelectDoubleClick)


def unregister():
    bpy.utils.unregister_class(ModozSelectDoubleClick)