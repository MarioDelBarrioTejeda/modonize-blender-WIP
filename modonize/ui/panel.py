# SPDX-License-Identifier: GPL-2.0-or-later

"""Panel de estado del sistema de selección en Edit Mode."""

import bpy

from ..selection import mode_memory
from .. import _state


class ModonizePanel(bpy.types.Panel):
    bl_label = "Modonize — Selección"
    bl_idname = "VIEW3D_PT_modonize_selection"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Modonize"

    @classmethod
    def poll(cls, context):
        prefs = _state.prefs(context)
        obj = context.active_object
        return (
            prefs.enable_selection
            and obj is not None
            and obj.type == "MESH"
            and obj.mode == "EDIT"
        )

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        mesh = obj.data
        ts = context.tool_settings
        sel = ts.mesh_select_mode

        layout.label(text="Memoria de selección por modo", icon="RESTRICT_SELECT_OFF")

        for i, mode in enumerate(("VERT", "EDGE", "FACE")):
            row = layout.row(align=True)
            active = sel[i]
            row.alert = active
            label = "Vértices" if mode == "VERT" else "Aristas" if mode == "EDGE" else "Caras"
            row.label(text=label, icon="SELECT_SET" if active else "DOT")
            if mode_memory.has_saved(mesh, mode):
                snap = mode_memory.get_saved(mesh, mode)
                row.label(text=f"{len(snap[mode[0]])} guardado", icon="FILE_TICK")
            else:
                row.label(text="(sin memoria)", icon="MUTE_IPO_ON")

        layout.separator()
        op = layout.operator("modoz.cycle_select_mode", text="Ciclar modo (Espacio)")


def register():
    _state.register_class_safe(ModonizePanel)


def unregister():
    _state.unregister_class_safe(ModonizePanel)