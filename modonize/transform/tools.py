# SPDX-License-Identifier: GPL-2.0-or-later

"""Fase 2 (Opción A): W/E/R -> tools nativos de transformación.

W/E/R seleccionan los tools de Blender (`builtin.move/rotate/scale`) vía
`wm.tool_set_by_id`, heredando gizmo, pivot, orientaciones y snapping.

En modo inmediato (`transform_immediate`), W/E/R ejecutan los transforms
nativos al instante (translate/rotate/resize). Además se añade W al
'Transform Modal Map' para que, durante un translate activo, pulsar W otra
vez conmute a Vertex/Edge Slide (los "railes" de las aristas conectadas),
igual que el G-G nativo; W-W-W vuelve a mover.

En el 3D View, W arranca `modoz.w_move` y E `modoz.e_rotate` (ver
view_transform.py): W mueve en los dos ejes que miran a la vista y E rota
solo alrededor del eje de profundidad, calculado en el espacio de la
orientación de transformación activa (Global, Local, View, personalizada...);
con orientación Normal, W mueve solo a lo largo de la normal y E rota sobre
ella. En el resto de editores W y E siguen siendo los transforms nativos
libres.

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
    "Sequencer",
    "SequencerPreview",
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

    # W/E/R unificados en todos los editores: 3D, UV, keyframes (Graph/Dope/NLA),
    # nodos y secuenciador (VSE). transform.translate/rotate/resize se adaptan
    # al contexto activo.
    for km_name in _EDITOR_KEYMAPS:
        km = kc.keymaps.get(km_name)
        if km is None:
            continue
        if prefs.transform_immediate:
            # Modo inmediato: W/E/R transforman al instante, como G/R/S.
            # En el 3D View, W/E pasan por modoz.w_move/modoz.e_rotate:
            # translate pre-restringido a los dos ejes que miran a la vista y
            # rotate sobre el eje de profundidad, según la orientación activa
            # (ver view_transform.py).
            _view_ops = {"W": "modoz.w_move", "E": "modoz.e_rotate"}
            for key, opname in _immediate_slots().items():
                if km_name == "3D View" and key in _view_ops:
                    opname = _view_ops[key]
                kmi = km.keymap_items.new(opname, key, "PRESS", head=True)
                _addon_keymaps.append((km, kmi))
        else:
            # Modo herramienta: W/E/R seleccionan el tool nativo (gizmo).
            for key, tool in _builtin_slots().items():
                kmi = km.keymap_items.new("wm.tool_set_by_id", key, "PRESS", head=True)
                kmi.properties.name = tool
                _addon_keymaps.append((km, kmi))

    # W-W durante un translate activo conmuta a Vertex/Edge Slide (el "G-G"
    # nativo, pero con nuestra tecla). El filtrado por modo/contexto lo hace
    # el poll_modal_item del propio Transform Modal Map: VERT_EDGE_SLIDE solo
    # está activo durante TRANSLATION en mallas; TRANSLATE solo cuando el modo
    # actual no es translate (así W-W-W vuelve a mover).
    if prefs.transform_immediate:
        modal_km = kc.keymaps.get("Transform Modal Map")
        if modal_km is not None:
            for propvalue in ("VERT_EDGE_SLIDE", "TRANSLATE"):
                kmi = modal_km.keymap_items.new_modal(propvalue, "W", "PRESS")
                _addon_keymaps.append((modal_km, kmi))


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