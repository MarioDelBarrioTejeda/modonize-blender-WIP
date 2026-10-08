# SPDX-License-Identifier: GPL-2.0-or-later

"""Paletas de color por modo de selección de componentes (Vértices/Aristas/Caras).

Blender usa una única paleta de tema para elementos seleccionados. Este módulo
la sustituye por una paleta por modo de selección mientras el addon está activo:

- Reescribe los colores del tema activo (``themes[...].view_3d``) según el modo.
- Ajusta la opacidad de wireframe de las vistas 3D (α 0.1 en modo caras).
- Captura los valores originales al activarse y los restaura al desactivarse.

Diseño validado en Blender 5.2 (tabla): caras seleccionadas transparentes en
modos vértice/arista, aristas muy tenues en modo caras, mismo hue base.
"""

import bpy

from .. import _state

# Paleta por modo según la tabla diseñada (valores RGBA/RGB y estilos).
_GRIS = (0.25, 0.25, 0.25)   # wireframe y aristas en modos vértices/aristas (oscuro)
_GRIS_VERT = (0.15, 0.15, 0.15)  # vértices aún más oscuros en modo vértices
_GRIS_MUY_OSCURO = (0.1, 0.1, 0.1)  # aristas no seleccionadas en modo caras: casi invisibles

_PALETTES = {
    "VERT": {
        "vertex_select": (1.0, 0.478, 0.0),
        # Aristas seleccionadas invisibles en modo vértices: mismo gris que el
        # wireframe, así no destacan ninguna.
        "edge_select": _GRIS,
        "face_select": (1.0, 0.639, 0.0, 0.0),  # caras transparentes
        "editmesh_active": (1.0, 1.0, 1.0, 0.2),
        "edge_width": 1,
        "vertex_size": 4,  # seleccionados: tamaño inicial + 1 (los no seleccionados quedan como puntitos)
        "face_mode_select": (1.0, 0.718, 0.0, 0.0),
        "edge_mode_select": _GRIS,
        # Aristas con el MISMO tono que en modo caras (gris 0.25): solo el
        # modo aristas las marca más (gris 0.1).
        "wire_edit": _GRIS,
        "vertex": _GRIS_VERT,
        "wireframe_opacity": 1.0,
        "show_wireframes": False,
    },
    "EDGE": {
        "vertex_select": (1.0, 0.478, 0.0),
        "edge_select": (1.0, 0.6, 0.0),
        "face_select": (1.0, 0.639, 0.0, 0.0),  # caras transparentes
        "editmesh_active": (1.0, 1.0, 1.0, 0.2),
        "edge_width": 1,
        "vertex_size": 3,
        "face_mode_select": (1.0, 0.718, 0.0, 0.0),
        "edge_mode_select": (1.0, 0.8, 0.0),
        # Aristas no seleccionadas MUY marcadas en modo aristas (gris casi
        # negro, máximo contraste).
        "wire_edit": _GRIS_MUY_OSCURO,
        "vertex": _GRIS_MUY_OSCURO,
        "wireframe_opacity": 1.0,
        "show_wireframes": False,
    },
    "FACE": {
        "vertex_select": (1.0, 0.478, 0.0),
        "edge_select": (1.0, 0.6, 0.0),
        "face_select": (1.0, 0.639, 0.0, 0.2),
        "editmesh_active": (1.0, 1.0, 1.0, 0.2),
        "edge_width": 1,
        "vertex_size": 3,
        "face_mode_select": (1.0, 0.718, 0.0, 0.2),
        "edge_mode_select": (1.0, 0.8, 0.0),
        # Aristas no seleccionadas tenues en modo caras (gris más claro que
        # el de modo aristas, menos contraste) + overlay al mínimo.
        "wire_edit": _GRIS,
        "vertex": _GRIS,
        "wireframe_opacity": 0.05,
        "show_wireframes": True,
    },
}

# Propiedades del tema que tocamos (las que existan en la versión actual).
_THEME_PROPS = (
    "vertex_select",
    "edge_select",
    "face_select",
    "editmesh_active",
    "edge_width",
    "vertex_size",
    "face_mode_select",
    "edge_mode_select",
    "wire_edit",
    "vertex",
)

_ORIG_THEME = {}   # {prop: valor original del tema}
_ORIG_OVERLAY = {}  # {id(space): (wireframe_opacity, show_wireframes) originales}
_ACTIVE = False


def _theme():
    """Devuelve el ``view_3d`` del tema activo (usa 'Default' o el primero)."""
    themes = bpy.context.preferences.themes
    if "Default" in themes:
        return themes["Default"].view_3d
    return themes[0].view_3d


def _view3d_spaces():
    """Lista de espacios 3D únicos en uso (ventanas reales).

    Defensivo: 
    - Nunca debe fallar: ``bpy.data`` puede estar restringido durante el
      registro del addon (screens/window_managers no accesibles); en ese caso
      se devuelve la lista vacía y los espacios se procesan en el primer uso
      real (apply/restore cuando hay ventanas).
    - Se filtran con isinstance de SpaceView3D (áreas en segundo plano pueden
      apuntar a otro tipo de espacio).
    """
    try:
        wms = list(bpy.data.window_managers)
    except Exception:
        return []
    seen = set()
    out = []
    for wm in wms:
        for win in wm.windows:
            screen = getattr(win, "screen", None)
            if screen is None:
                continue
            for area in screen.areas:
                try:
                    space = area.spaces.active
                except Exception:
                    continue
                if not isinstance(space, bpy.types.SpaceView3D):
                    continue
                if id(space) in seen:
                    continue
                seen.add(id(space))
                out.append(space)
    return out


def _as_py(value):
    """Convierte un valor del tema a tipo Python plano (los int/float se
    devuelven tal cual; los colores, como tupla)."""
    if isinstance(value, (int, float)):
        return value
    return tuple(value)


def capture():
    """Guarda los valores originales del tema.

    Solo captura la primera vez: un re-registro sin desactivar no debe
    sobreescribir los originales con la paleta ya aplicada (evita "contaminar"
    la línea base). Tras ``restore()`` los diccionarios quedan vacíos y se
    recaptura limpio en el siguiente registro.
    """
    th = _theme()
    for prop in _THEME_PROPS:
        if hasattr(th, prop) and prop not in _ORIG_THEME:
            _ORIG_THEME[prop] = _as_py(getattr(th, prop))


def apply(mode):
    """Aplica la paleta del modo ``mode`` (VERT/EDGE/FACE)."""
    if mode not in _PALETTES:
        return
    pal = _PALETTES[mode]
    th = _theme()
    for prop in _THEME_PROPS:
        if prop in pal and hasattr(th, prop):
            setattr(th, prop, pal[prop])
    for sp in _view3d_spaces():
        try:
            # Guardar (opacidad, show_wireframes) originales la 1ª vez.
            _ORIG_OVERLAY.setdefault(
                id(sp),
                (sp.overlay.wireframe_opacity, sp.overlay.show_wireframes),
            )
            if "wireframe_opacity" in pal:
                sp.overlay.wireframe_opacity = pal["wireframe_opacity"]
            if "show_wireframes" in pal:
                sp.overlay.show_wireframes = pal["show_wireframes"]
        except Exception:
            pass


def reset_display():
    """Vuelve el tema y los overlays a sus valores originales SIN perder la
    línea base capturada.

    Se usa al salir de Edit Mode (o cuando no hay una malla en edición): la
    paleta del modo de componentes solo debe existir dentro de Edit Mode. A
    diferencia de ``restore()``, conserva ``_ORIG_THEME``/``_ORIG_OVERLAY`` para
    poder volver a aplicar la paleta al reentrar en edición.
    """
    th = _theme()
    for prop, value in _ORIG_THEME.items():
        try:
            setattr(th, prop, value)
        except Exception:
            pass
    for sp in _view3d_spaces():
        orig = _ORIG_OVERLAY.get(id(sp))
        if orig is not None:
            try:
                sp.overlay.wireframe_opacity = orig[0]
                sp.overlay.show_wireframes = orig[1]
            except Exception:
                pass


def restore():
    """Restaura los valores originales del tema y del overlay de las vistas y
    descarta la línea base (para desregistrar el addon)."""
    reset_display()
    _ORIG_THEME.clear()
    _ORIG_OVERLAY.clear()


def _on_change(*_args, **_kwargs):
    """Callback de cambio: aplica la paleta del modo actual (si procede).

    Blender 5.2 no notifica por msgbus los cambios de ``mesh_select_mode`` ni
    de ``Object.mode`` (comprobado), así que se usa un handler de depsgraph
    que compara el estado y solo aplica cuando cambia de verdad.
    """
    global _ACTIVE
    if not _ACTIVE:
        return
    prefs = _state.prefs(bpy.context)
    if not prefs.enable_selection:
        return
    try:
        obj = bpy.context.active_object
        if obj is not None and obj.type == "MESH" and obj.mode == "EDIT":
            apply(_state.current_component_mode(bpy.context))
        else:
            # Fuera de Edit Mode el aspecto debe ser el de por defecto.
            reset_display()
    except Exception:
        pass


_last_state = [None]  # cache (in_edit, mesh_select_mode) para evitar trabajo redundante


def _depsgraph_cb(_depsgraph):
    if not _ACTIVE:
        return
    try:
        obj = bpy.context.view_layer.objects.active
        in_edit = obj is not None and obj.type == "MESH" and obj.mode == "EDIT"
        mode = tuple(bpy.context.tool_settings.mesh_select_mode)
        key = (in_edit, mode)
        if key != _last_state[0]:
            _last_state[0] = key
            if in_edit:
                apply(_state.current_component_mode(bpy.context))
            else:
                # Al salir de Edit Mode, restaurar el aspecto por defecto del
                # modo objeto (tema y overlays).
                reset_display()
    except Exception:
        pass


def _subscribe():
    """Escucha cambios de modo de selección (incluido desde el header)."""
    if _depsgraph_cb not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_depsgraph_cb)


def _unsubscribe():
    try:
        bpy.app.handlers.depsgraph_update_post.remove(_depsgraph_cb)
    except ValueError:
        pass


def register():
    global _ACTIVE, _last_state
    prefs = _state.prefs(bpy.context)
    if not prefs.enable_selection:
        return
    _last_state = [None]
    capture()
    _subscribe()
    _ACTIVE = True
    _on_change()


def unregister():
    global _ACTIVE
    _ACTIVE = False
    _unsubscribe()
    restore()