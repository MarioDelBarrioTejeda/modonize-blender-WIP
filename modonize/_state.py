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


def register_class_safe(cls):
    """Registra una clase. Si ya estaba registrada (reload/fallo parcial), la
    desregistra primero y la registra de nuevo (idempotente)."""
    import bpy
    try:
        bpy.utils.unregister_class(cls)
    except Exception:
        pass
    return bpy.utils.register_class(cls)


def unregister_class_safe(cls):
    try:
        import bpy
        bpy.utils.unregister_class(cls)
    except Exception:
        pass


def register_tool_safe(clazz):
    """Registra un WorkSpaceTool. Si ya existe el idname, lo elimina y lo
    vuelve a registrar (idempotente en reloads de desarrollo)."""
    import bpy
    try:
        bpy.utils.unregister_tool(clazz)
    except Exception:
        pass
    bpy.utils.register_tool(clazz)


def prestada_off(kc, keymap_names, types):
    """'Tecla prestada': desactiva los items ajenos de `types` en los keymaps
    indicados. Devuelve [(km, kmi)] para restaurarlos con `prestada_restore`."""
    out = []
    for name in keymap_names:
        km = kc.keymaps.get(name)
        if km is None:
            continue
        for kmi in km.keymap_items:
            if kmi.type in types and kmi.active:
                out.append((km, kmi))
                kmi.active = False
    return out


def prestada_restore(items):
    for km, kmi in items:
        try:
            kmi.active = True
        except Exception:
            pass