# SPDX-License-Identifier: GPL-2.0-or-later

"""Atajos de edición de malla (enlazados sobre el keymap 'Mesh').

- [DOWN]/[UP]          -> seleccionar siguiente / anterior
- [SHIFT+DOWN]/[SHIFT+UP] -> seleccionar más / menos
- [B]                  -> bevel (sustituye el box-select de Blender)
- [L]                  -> seleccionar loop (sustituye select-linked)
- [D]                  -> subdividir malla

Los defaults de Blender que chocan (B box-select, L select-linked, D) se
desactivan temporalmente y se restauran al apagar el addon ("tecla prestada").
"""

import bpy

from .. import _state

_addon_keymaps = []          # (km, kmi) nuestros
_prestada = []               # (km, kmi) defaults desactivados

# _temporarily_disabled (alias para compatibilidad con otros módulos)
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

    km = kc.keymaps.get("Mesh")
    if km is None:
        return

    global _addon_keymaps, _prestada, _temporarily_disabled

    # Desactivar defaults que reemplazamos (B, L, D) en 'Mesh'.
    _prestada = _state.prestada_off(kc, ("Mesh",), {"B", "L", "D"})
    _temporarily_disabled = list(_prestada)

    def add(key, op, shift=False, head=True):
        kmi = km.keymap_items.new(op, key, "PRESS", shift=shift, head=head)
        _addon_keymaps.append((km, kmi))

    add("UP_ARROW", "mesh.select_next_item")
    add("DOWN_ARROW", "mesh.select_prev_item")
    add("UP_ARROW", "mesh.select_more", shift=True)
    add("DOWN_ARROW", "mesh.select_less", shift=True)
    add("B", "mesh.bevel")
    add("L", "modoz.select_loop")
    add("D", "mesh.subdivide")


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