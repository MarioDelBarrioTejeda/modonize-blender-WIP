# SPDX-License-Identifier: GPL-2.0-or-later

"""Atajos del Secuenciador (VSE), enlazados sobre el keymap 'Sequencer'.

- [D] -> sequencer.knife (herramienta cuchillo: corta los strips que cruza
  el arrastre del ratón; corta varios strips de un solo gesto).

El item se registra con `head=True` para evaluarlo antes que cualquier
asignación por defecto de la tecla D; si el `poll` de `sequencer.knife`
falla, Blender continúa con el resto del keymap.
"""

import bpy

from .. import _state

_addon_keymaps = []          # (km, kmi) nuestros


def register():
    prefs = _state.prefs(bpy.context)
    if not prefs.enable_editor:
        return

    kc = bpy.context.window_manager.keyconfigs.active
    if kc is None:
        kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:
        return

    km = kc.keymaps.get("Sequencer")
    if km is None:
        return

    kmi = km.keymap_items.new("sequencer.knife", "D", "PRESS", head=True)
    _addon_keymaps.append((km, kmi))


def unregister():
    global _addon_keymaps
    for km, kmi in _addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _addon_keymaps = []
