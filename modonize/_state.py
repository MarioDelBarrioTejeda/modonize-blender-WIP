# SPDX-License-Identifier: GPL-2.0-or-later

"""Estado compartido del addon.

`bl_idname` de las preferencias es la raíz del paquete ('modonize'). Cualquier
submódulo (modonize.selection, modonize.ui, ...) que necesite las preferencias
debe usar `_state.prefs(context)` en lugar de `bpy.context.preferences.addons[__package__]`,
porque ahí `__package__` sería 'modonize.selection' y no 'modonize'.
"""

ADDON_PACKAGE = __package__  # 'modonize' (módulo de nivel raíz)


def prefs(context):
    return context.preferences.addons[ADDON_PACKAGE].preferences