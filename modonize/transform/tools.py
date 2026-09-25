# SPDX-License-Identifier: GPL-2.0-or-later

"""Fase 2 (Opción A): W/E/R -> tools nativos de transformación.

W/E/R seleccionan los tools de Blender (`builtin.move/rotate/scale`) vía
`wm.tool_set_by_id`, heredando gizmo, pivot, orientaciones y snapping.

Como W/E/R tienen usos por defecto en Blender (W cicla selección, E extruye en
edit, R rota modal), esos defaults se **desactivan temporalmente** mientras el
addon está activo y se **restauran** al apagarlo (tecla "prestada").

El arrastre fuera del gizmo queda con el comportamiento nativo de Blender
(selección / mover si "Drag: Active tool"). El snap al eje dominante en el
arrastre (spec) queda como refinamiento opcional futuro (Opción B).
"""

import bpy

from .. import _state

_addon_keymaps = []          # (keymap, item) nuestros
_temporarily_disabled = []   # items ajenos desactivados: (km, kmi)


def _builtin_slots():
    return {"W": "builtin.move", "E": "builtin.rotate", "R": "builtin.scale"}


def _disable_defaults(kc, keys):
    for km_name in ("3D View", "Object Mode", "Mesh"):
        km = kc.keymaps.get(km_name)
        if km is None:
            continue
        for kmi in km.keymap_items:
            if kmi.type in keys and kmi.active:
                _temporarily_disabled.append((km, kmi))
                kmi.active = False


def register():
    prefs = _state.prefs(bpy.context)
    if not prefs.enable_transform:
        return

    kc = bpy.context.window_manager.keyconfigs.active
    if kc is None:
        kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:
        return

    _disable_defaults(kc, set(_builtin_slots()))

    km = kc.keymaps.get("3D View")
    if km is None:
        return
    for key, tool in _builtin_slots().items():
        kmi = km.keymap_items.new("wm.tool_set_by_id", key, "PRESS", head=True)
        kmi.properties.name = tool
        _addon_keymaps.append((km, kmi))


def unregister():
    global _addon_keymaps, _temporarily_disabled
    for km, kmi in _temporarily_disabled:
        try:
            kmi.active = True
        except Exception:
            pass
    _temporarily_disabled = []
    for km, kmi in _addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _addon_keymaps = []