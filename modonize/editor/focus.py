# SPDX-License-Identifier: GPL-2.0-or-later

"""Tecla [F]: enfocar la selección en cada editor.

- 3D View   -> view3d.view_selected
- Node Editor -> node.view_selected (Geometry, Shader, Compositor)
- Outliner  -> outliner.show_active (centrar en el elemento activo)

Nota: el UV Editor no expone un `view_selected` (limitación del API), por lo
que queda fuera de momento.
"""

import bpy

from .. import _state

_addon_keymaps = []
_prestada = []          # (km, kmi) defaults desactivados (p. ej. F=fill en Mesh)
_temporarily_disabled = []


def register():
    prefs = _state.prefs(bpy.context)
    if not prefs.enable_editor:
        return

    kc = bpy.context.window_manager.keyconfigs.active
    if kc is None:
        kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:
        return

    global _addon_keymaps, _prestada, _temporarily_disabled

    # F=fill en edit mesh choca con enfocar; lo desactivamos y lo restauramos.
    _prestada = _state.prestada_off(kc, ("Mesh",), {"F"})
    _temporarily_disabled = list(_prestada)

    for km_name, op in (
        ("3D View", "view3d.view_selected"),
        ("Node Editor", "node.view_selected"),
        ("Outliner", "outliner.show_active"),
    ):
        km = kc.keymaps.get(km_name)
        if km is None:
            continue
        kmi = km.keymap_items.new(op, "F", "PRESS", head=True)
        _addon_keymaps.append((km, kmi))


def unregister():
    global _addon_keymaps, _prestada, _temporarily_disabled
    for km, kmi in _addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _addon_keymaps = []
    _state.prestada_restore(_prestada)
    _prestada = []
    _temporarily_disabled = []