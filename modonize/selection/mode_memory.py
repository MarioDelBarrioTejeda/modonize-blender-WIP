# SPDX-License-Identifier: GPL-2.0-or-later

"""Caché de la selección por modo de componente (Vértices/Aristas/Caras).

Blender, por defecto, *convierte* la selección al cambiar de modo de componente
(vértices -> aristas, etc.). Este módulo guarda, por malla y por modo, el último
estado de selección para poder restaurarlo al volver a ese modo (memoria Modo).

La clave de la caché es el objeto ``Mesh`` (los datos de malla) porque la
selección de edit mode vive en el propio mesh y es compartida por varios objetos
que referencien la misma malla.

El snapshot guarda índices bmesh. Como los índices pueden volverse inválidos al
cambiar la topología (subdividir, extruir...), cada snapshot lleva una
"signatura" (número de vértices/aristas/caras). Al restaurar, si la topología
actual difiere de la guardada, se descarta la memoria (degradación segura).
"""

import bmesh

# {Mesh: {modo: snapshot}}
_MEMORY = {}

_MODE_KEY = {"VERT": "V", "EDGE": "E", "FACE": "F"}
# Componentes bmesh asociados a cada modo de selección.
_BM_ATTR = {"VERT": "verts", "EDGE": "edges", "FACE": "faces"}


def _bm(mesh):
    bm = bmesh.from_edit_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    return bm


def snapshot(mesh):
    """Toma un snapshot completo de la selección actual de ``mesh``."""
    bm = _bm(mesh)
    return {
        "V": [v.index for v in bm.verts if v.select],
        "E": [e.index for e in bm.edges if e.select],
        "F": [f.index for f in bm.faces if f.select],
        "sig": (len(bm.verts), len(bm.edges), len(bm.faces)),
    }


def counts(mesh):
    """Devuelve el número actual de vértices/aristas/caras de ``mesh``."""
    bm = _bm(mesh)
    return (len(bm.verts), len(bm.edges), len(bm.faces))


def save_mode(mesh, mode, snap=None):
    """Guarda la selección (o un snapshot dado) para ``mode``."""
    if snap is None:
        snap = snapshot(mesh)
    _MEMORY.setdefault(mesh, {})[mode] = snap


def get_saved(mesh, mode):
    """Devuelve el snapshot guardado para ``mode`` o ``None`` si no hay."""
    return _MEMORY.get(mesh, {}).get(mode)


def has_saved(mesh, mode):
    return mode in _MEMORY.get(mesh, {})


def restore_mode(mesh, mode, snap=None):
    """Restaura la selección de ``mode`` desde la caché.

    Si la topología cambió desde que se guardó el snapshot, no se restaura nada
    (degradación segura) para no aplicar índices inválidos.
    """
    if snap is None:
        snap = get_saved(mesh, mode)
    if not snap:
        return False

    bm = _bm(mesh)
    if counts(mesh) != snap["sig"]:
        return False

    key = _MODE_KEY[mode]
    attr = _BM_ATTR[mode]
    elems = getattr(bm, attr)

    # Deseleccionar todo en el modo entrante y restaurar la memoria.
    if mode == "VERT":
        for v in bm.verts:
            v.select = False
    elif mode == "EDGE":
        for e in bm.edges:
            e.select = False
    else:
        for f in bm.faces:
            f.select = False

    for idx in snap[key]:
        if idx < len(elems):
            elems[idx].select = True

    bm.select_flush_mode()
    bmesh.update_edit_mesh(mesh)
    return True


def invalidate(mesh):
    """Descarta la memoria de una malla (p. ej. al salir de edit mode)."""
    _MEMORY.pop(mesh, None)


def clear_all():
    _MEMORY.clear()