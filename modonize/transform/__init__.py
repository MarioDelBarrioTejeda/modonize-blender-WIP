# SPDX-License-Identifier: GPL-2.0-or-later

"""Fase 2 (Opción A): Sistema de Transformación.

W/E/R seleccionan los tools nativos de Blender (`builtin.move/rotate/scale`),
heredando gizmo, pivot, orientaciones y snapping. No se reimplementa nada.

(Los módulos custom previos —drag_ops, gizmo, overlay— quedan fuera hasta que
se quiera retomar la variación del eje dominante, Opción B.)
"""

from . import tools


def register():
    tools.register()


def unregister():
    tools.unregister()