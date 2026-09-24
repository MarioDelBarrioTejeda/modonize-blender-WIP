# SPDX-License-Identifier: GPL-2.0-or-later

"""Handler de depsgraph para mantener la memoria de selección por modo incluso
cuando el modo cambia por vías ajenas al operador de ciclo (pestañas del header,
teclas 1/2/3, Ctrl+Tab, etc.).

Blender no expone un evento "cambio de modo de selección". La única vía fiable es
comparar, en `depsgraph_update_post`, el modo de cada malla en edit mode contra
el último visto. Para no penalizar el rendimiento:

- La pasada es ligera: itera objetos, solo hace trabajo si el objeto está en
  edit mode y su modo cambió, o la topología (número de elementos) cambió.
- Restaurar la memoria sólo ocurre al entrar en un modo o cambiar de modo.

La vía principal y síncrona de memoria es el operador de ciclo (SPACE), que
siempre toma un snapshot fresco. Este handler es de soporte (best-effort).
"""

import bpy

from . import mode_memory
from .. import _state

# {Mesh: (modo, siguta)}
_last = {}


def _mode_from_mesh(mesh):
    if mesh.use_mesh_sel_mode_face:
        return "FACE"
    if mesh.use_mesh_sel_mode_edge:
        return "EDGE"
    if mesh.use_mesh_sel_mode_vert:
        return "VERT"
    return None


def _is_enabled():
    try:
        ctx = bpy.context
        if ctx is None:
            return False
        return bool(_state.prefs(ctx).enable_selection)
    except Exception:
        # Si las preferencias no están accesibles (arranque, estados
        # transitorios), el handler no hace nada: nunca debe tirar errores
        # a la consola de Blender en cada actualización de la escena.
        return False


def _sync(scene, depsgraph):
    try:
        if not _is_enabled():
            return
        for obj in bpy.data.objects:
            if obj.type != "MESH" or obj.mode != "EDIT":
                _last.pop(obj.data, None)
                continue
            mesh = obj.data
            cur = _mode_from_mesh(mesh)
            if cur is None:
                _last.pop(mesh, None)
                continue
            prev = _last.get(mesh)
            if prev is None:
                # Al entrar en un modo, restaurar la memoria guardada.
                mode_memory.restore_mode(mesh, cur)
                _last[mesh] = (cur, mode_memory.counts(mesh))
                continue
            prev_mode, prev_sig = prev
            if prev_mode != cur:
                # Cambio de modo por vía externa: restaurar memoria del entrante.
                mode_memory.restore_mode(mesh, cur)
                _last[mesh] = (cur, mode_memory.counts(mesh))
            else:
                # Mismo modo: refrescar la caché sólo si cambió la topología.
                cur_sig = mode_memory.counts(mesh)
                if prev_sig != cur_sig:
                    mode_memory.save_mode(mesh, cur)
                    _last[mesh] = (cur, cur_sig)
    except Exception:
        # Nunca dejar que un error del handler rompa Blender ni ensucie la
        # consola repitiéndose en cada actualización de la escena.
        pass


def register():
    global _handler
    if "_handler" in globals() and _handler is not None:
        return
    _handler = bpy.app.handlers.depsgraph_update_post.append(_sync)


def unregister():
    global _handler
    if _handler is None:
        return
    if _handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_handler)
    _handler = None