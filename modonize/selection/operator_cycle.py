# SPDX-License-Identifier: GPL-2.0-or-later

"""Operador de ciclo de modo de selección (tecla por defecto: Espacio).

En Edit Mode de mallas, alterna el modo de selección de componentes en el orden
Vértices -> Aristas -> Caras -> Vértices. Antes de cambiar, vuelca la selección
del modo saliente a la caché; al entrar en el siguiente modo, restaura la
selección que ese modo tenía guardada (memoria independiente por modo).
"""

import bpy

from . import mode_memory

MODES = ("VERT", "EDGE", "FACE")


def _current_mode(context):
    ts = context.tool_settings
    sel = ts.mesh_select_mode  # tuple (vert, edge, face)
    if sel[0]:
        return "VERT"
    if sel[1]:
        return "EDGE"
    if sel[2]:
        return "FACE"
    return "VERT"


def _set_mode(context, mode):
    context.tool_settings.mesh_select_mode = [
        m == mode for m in MODES
    ]


class ModozCycleSelectMode(bpy.types.Operator):
    bl_idname = "modoz.cycle_select_mode"
    bl_label = "Ciclar modo de selección (Vértices/Aristas/Caras)"
    bl_description = (
        "Alterna entre Vértices, Aristas y Caras conservando la selección "
        "independiente de cada modo."
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"

    def execute(self, context):
        try:
            objs = [
                o for o in context.objects_in_mode_edit_mode
                if o is not None and o.type == "MESH"
            ]
        except Exception:
            objs = []
        if not objs:
            obj = context.active_object
            objs = [obj] if obj is not None and obj.type == "MESH" else []

        # 1) Guardar la selección del modo actual para cada objeto.
        current = _current_mode(context)
        for obj in objs:
            mesh = obj.data
            mode_memory.save_mode(mesh, current)

        # 2) Avanzar al siguiente modo.
        next_mode = MODES[(MODES.index(current) + 1) % len(MODES)]
        _set_mode(context, next_mode)

        # 3) Restaurar la selección que el siguiente modo tenía guardada.
        for obj in objs:
            mesh = obj.data
            mode_memory.restore_mode(mesh, next_mode)

        return {"FINISHED"}


def register():
    bpy.utils.register_class(ModozCycleSelectMode)


def unregister():
    bpy.utils.unregister_class(ModozCycleSelectMode)