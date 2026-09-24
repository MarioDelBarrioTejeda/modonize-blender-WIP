# SPDX-License-Identifier: GPL-2.0-or-later

"""Registro de atajos de teclado del addon.

- Tecla configurada (por defecto Espacio) en Edit Mode de malla: cicla modos.
- Doble clic con el botón izquierdo en Edit Mode de malla: gestos de selección.

Los items se registran **sobre el keyconfig activo** (`wm.keyconfigs.active`),
que es el conjunto de keymaps que Blender evalúa de verdad al procesar eventos.
Registrar en `wm.keyconfigs.addon` puede fallar silenciosamente cuando coexisten
varios keymaps con el mismo nombre ('Mesh') y nuestros items caen en una copia
que nunca se evalúa.

Para ganar incluso si otro addon/tecla consume SPACE antes en la pila:
- El ciclo se enlaza en 'Mesh' (edit mode) Y en '3D View' (genérico, evaluado
  antes). El `poll` del operador exige estar en edit mode con malla activa, así
  que en object mode el item no gana (poll falla) y las demás asignaciones de
  SPACE siguen funcionando.
- El doble clic se enlaza en 'Mesh'.

`head=True` coloca nuestros items primeros dentro de su keymap. En `unregister`
se eliminan SOLO nuestros items (nunca se borran keymaps compartidos).
"""

import bpy

from . import _state

# items registrados: lista de (KeyMap, KeyMapItem)
_addon_keymaps = []

# items ajenos al addon que hemos desactivado temporalmente: (km, kmi)
_temporarily_disabled = []


def _temporarily_disable_cycle_key(cycle_key):
    """Inhabilita items de la tecla de ciclo en el keymap 'Mesh' (edit mode)
    que no sean nuestros, guardándolos para restaurarlos en `unregister`.
    Sólo se toca 'Mesh': la barra espaciadora queda libre únicamente en edit
    mode mientras el addon está activo."""
    wm = bpy.context.window_manager
    for kc in (wm.keyconfigs.default, wm.keyconfigs.active):
        if kc is None:
            continue
        km = kc.keymaps.get("Mesh")
        if km is None:
            continue
        for kmi in km.keymap_items:
            if kmi.type == cycle_key and kmi.active and not kmi.idname.startswith("modoz."):
                _temporarily_disabled.append((km, kmi))
                kmi.active = False


def _bind_keymaps(cycle_key):
    """Registra los items sobre los keymaps del keyconfig activo.

    Devuelve la lista de (km, kmi) registrados para poder limpiarlos después.
    """
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.active or wm.keyconfigs.addon
    bound = []
    if kc is None:
        return bound

    mesh_km = kc.keymaps.get("Mesh")
    if mesh_km is not None:
        bound.append(
            (mesh_km, mesh_km.keymap_items.new(
                "modoz.cycle_select_mode", cycle_key, "PRESS", head=True
            ))
        )
        bound.append(
            (mesh_km, mesh_km.keymap_items.new(
                "modoz.select_double_click", "LEFTMOUSE", "DOUBLE_CLICK", head=True
            ))
        )

    # Respaldo en el keymap genérico del visor (se evalúa antes que 'Mesh'):
    # sólo gana en edit mode gracias al poll; en object mode el poll falla y
    # las otras asignaciones de SPACE siguen activas.
    view_km = kc.keymaps.get("3D View")
    if view_km is not None:
        bound.append(
            (view_km, view_km.keymap_items.new(
                "modoz.cycle_select_mode", cycle_key, "PRESS", head=True
            ))
        )
    return bound


def register():
    prefs = _state.prefs(bpy.context)
    if not prefs.enable_selection:
        return

    cycle_key = prefs.cycle_key

    # Dejar libre la tecla de ciclo en edit mode (restaurar en unregister).
    _temporarily_disable_cycle_key(cycle_key)

    _addon_keymaps.extend(_bind_keymaps(cycle_key))


def unregister():
    global _addon_keymaps, _temporarily_disabled

    # Restaurar los items ajenos que habíamos desactivado temporalmente.
    # Nota: `kmi.name` es la etiqueta (no el idname), por lo que no se puede
    # usar como clave de pertenencia en keymap_items.
    for km, kmi in _temporarily_disabled:
        try:
            kmi.active = True
        except Exception:
            pass
    _temporarily_disabled = []

    # Eliminar SOLO nuestros items (nunca los keymaps, que son compartidos).
    for km, kmi in _addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _addon_keymaps = []