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


def _immediate_slots():
    """W/E/R transforman al instante con los operadores de G/R/S."""
    return {
        "W": "transform.translate",
        "E": "transform.rotate",
        "R": "transform.resize",
    }


_EDITOR_KEYMAPS = (
    "3D View",
    "UV Editor",
    "Graph Editor",
    "Dope Sheet",
    "NLA Editor",
    "Node Editor",
)
_DISABLE_KEYMAPS = ("3D View", "Object Mode", "Mesh") + _EDITOR_KEYMAPS


def _disable_defaults(kc, keys):
    """Desactiva la tecla simple (W/E/R sin modificadores). Los atajos con
    Shift/Ctrl/Alt/OS (Shift+E crease, Alt+E extrude, ...) se conservan."""
    for km_name in _DISABLE_KEYMAPS:
        km = kc.keymaps.get(km_name)
        if km is None:
            continue
        for kmi in km.keymap_items:
            if (
                kmi.type in keys
                and kmi.active
                and not (kmi.shift or kmi.ctrl or kmi.alt or kmi.oskey)
            ):
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

    _disable_defaults(kc, {"W", "E", "R"})

    # W/E/R unificados en todos los editores: 3D, UV, keyframes (Graph/Dope/NLA)
    # y nodos. transform.translate/rotate/resize se adaptan al contexto activo.
    for km_name in _EDITOR_KEYMAPS:
        km = kc.keymaps.get(km_name)
        if km is None:
            continue
        if prefs.transform_immediate:
            # Modo inmediato: W/E/R transforman al instante, como G/R/S.
            for key, opname in _immediate_slots().items():
                kmi = km.keymap_items.new(opname, key, "PRESS", head=True)
                _addon_keymaps.append((km, kmi))
        else:
            # Modo herramienta: W/E/R seleccionan el tool nativo (gizmo).
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