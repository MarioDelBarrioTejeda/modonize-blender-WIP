# SPDX-License-Identifier: GPL-2.0-or-later

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    IntProperty,
    PointerProperty,
)

from . import _state


class ModonizePreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # --- Sistema de selección -------------------------------------------
    enable_selection: BoolProperty(
        name="Sistema de selección",
        description="Activa el sistema de selección de Modo en Edit Mode "
        "(ciclo de modos con la tecla configurada y memoria de selección por modo).",
        default=True,
    )

    cycle_key: EnumProperty(
        name="Tecla de ciclo de modo",
        description="Tecla que alterna entre Vértices / Aristas / Caras en Edit Mode.",
        items=(
            ("SPACE", "Espaci(space)", "Usa la barra espaciadora (recomendado)."),
            ("TAB", "Tab (TAB)", "Usa la tecla Tab para ciclar modos."),
        ),
        default="SPACE",
    )

    # Gesto de doble clic en modo arista (decisión abierta de la spec, L15 vs L19).
    edge_dbl_click: EnumProperty(
        name="Doble clic en arista",
        description="Qué hace el doble clic sobre una arista en modo Aristas.",
        items=(
            ("LOOP", "Seleccionar loop", "Selecciona el edge loop (línea 15 de la spec)."),
            ("CONNECTED", "Seleccionar malla", "Selecciona toda la malla unida (línea 19 de la spec)."),
        ),
        default="LOOP",
    )

    # --- Fase 2: sistema de transformación (herramientas Modo W/E/R) ------
    enable_transform: BoolProperty(
        name="Sistema de transformación (W/E/R)",
        description="Herramientas Modo Move/Rotate/Scale en el viewport: "
        "gizmo de Blender + arrastre en el plano del eje cartesiano dominante.",
        default=True,
    )
    enable_focus: BoolProperty(
        name="Tecla F (enfoque)",
        description="Enfoca la selección en 3D view, nodos y outliner.",
        default=False,
    )

    # --- Fase 3: atajos de editor (selección up/down, bevel, loops, subdiv) --
    enable_editor: BoolProperty(
        name="Atajos de edición",
        description="Atajos de edit mode: [UP]/[DOWN] prev/next, [SHIFT+UP/DOWN] "
        "more/less, [B] bevel, [L] loops, [D] subdividir, y tecla [F] de foco.",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "enable_selection")
        if self.enable_selection:
            box = layout.box()
            box.label(text="Sistema de selección", icon="RESTRICT_SELECT_OFF")
            box.prop(self, "cycle_key")
            box.prop(self, "edge_dbl_click")

        layout.separator()
        layout.prop(self, "enable_transform")
        layout.prop(self, "enable_focus")
        layout.prop(self, "enable_editor")


_classes = (ModonizePreferences,)


def register():
    for cls in _classes:
        _state.register_class_safe(cls)


def unregister():
    for cls in reversed(_classes):
        _state.unregister_class_safe(cls)