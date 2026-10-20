# SPDX-License-Identifier: GPL-2.0-or-later

"""Operadores W/E en el viewport 3D: mover y rotar según la vista.

Ambos tienen en cuenta la cámara y la orientación de transformación activa:

- `modoz.w_move` (W): mueve en los dos ejes que miran a la vista; se bloquea
  el eje de profundidad (el más alineado con la cámara en el espacio de la
  orientación activa): par XZ en alzado, XY en planta, YZ en perfil... el
  par equivalente en el espacio LOCAL si la orientación activa es Local. Con
  orientación `Normal`, W se mueve **solo a lo largo de la normal**
  (empujar/tirar).
- `modoz.e_rotate` (E): rota **solo alrededor del eje de la vista snapeado**
  en el espacio de la orientación activa: la dirección de la cámara se
  expresa en esa orientación y se cuantiza al eje local más frontal (X, Y o
  Z de la orientación); la rotación se restringe a ese eje con
  **`constraint_axis` + `orient_type` explícitos** (mismo sistema de
  restricciones que W y las teclas X/Y/Z: guía del eje y texto visibles,
  pivotes por elemento correctos). Con orientación `Normal`, rota alrededor
  de la normal de la selección.

W y E pasan `orient_type` explícito = orientación activa del slot, así la
restricción se aplica siempre en esa orientación sin depender de valores por
defecto; ambos usan `constraint_axis` (nunca `orient_axis`) para entrar por
el sistema de restricciones nativo. Nota: `Gimbal` usa la matriz Local
(equivale para el euler XYZ por defecto).

Durante el transform se pueden cambiar las restricciones con las teclas
nativas X/Y/Z (Transform Modal Map de Blender), y W-W sigue conmutando a
Vertex/Edge Slide. Fuera del 3D View (UV, nodos, secuenciador...) W y E
siguen siendo los transforms nativos libres (ver tools.py).
"""

import bpy
from mathutils import Matrix, Vector

from .. import _state


def _active_orientation_type(context):
    """Tipo de la orientación de transformación activa en el slot por
    defecto ('GLOBAL' si no hay slot)."""
    slots = getattr(context.scene, "transform_orientation_slots", None)
    slot = slots[0] if slots and len(slots) else None
    return slot.type if slot else "GLOBAL"


def _orientation_matrix(context):
    """Rotación (orientación -> mundo) de la orientación activa. None si no
    se puede determinar."""
    otype = _active_orientation_type(context)

    if otype == "GLOBAL":
        return Matrix.Identity(3)
    if otype in {"LOCAL", "GIMBAL"}:
        obj = context.object
        if obj is None:
            return None
        return obj.matrix_world.to_3x3().normalized()
    if otype == "VIEW":
        rv3d = getattr(context, "region_data", None)
        if rv3d is None:
            return None
        return rv3d.view_matrix.inverted_safe().to_3x3()
    if otype == "CURSOR":
        return context.scene.cursor.matrix.to_3x3()
    # Orientación personalizada del slot. En la API reciente (Blender 5.x)
    # vive en slot.custom_orientation; en las antiguas (4.x) en
    # scene.transform_orientations[index_custom]. Se blindan ambas rutas.
    custom = getattr(slot, "custom_orientation", None) if slot else None
    if custom is not None:
        return custom.matrix.to_3x3()
    customs = getattr(context.scene, "transform_orientations", None)
    idx = getattr(slot, "index_custom", -1) if slot else -1
    if customs and 0 <= idx < len(customs):
        return customs[idx].matrix.to_3x3()
    return None


def _view_axis_index(context):
    """Índice (0=X, 1=Y, 2=Z) del eje de la orientación activa más alineado
    con la vista (el eje de profundidad). Con `Normal` es siempre 2 (la
    normal de la selección). None si no es determinable."""
    if _active_orientation_type(context) == "NORMAL":
        return 2
    rv3d = getattr(context, "region_data", None)
    mat = _orientation_matrix(context)
    if rv3d is None or mat is None:
        return None
    # Dirección de la mirada de la cámara en espacio de mundo (mira por -Z local).
    view_dir = rv3d.view_matrix.inverted_safe().to_3x3() @ Vector((0.0, 0.0, -1.0))
    # Expresarla en el espacio de la orientación activa (matriz de rotación).
    local_dir = mat.inverted_safe() @ view_dir
    dots = (abs(local_dir.x), abs(local_dir.y), abs(local_dir.z))
    return max(range(3), key=dots.__getitem__)


def _translate_mask(context):
    """Máscara `constraint_axis` (x, y, z) para W en el espacio de la
    orientación activa. None si no hay vista 3D u orientación determinable.

    - Normal: solo el eje Z (la normal media de la selección).
    - Resto: los dos ejes que miran a la vista (se bloquea el de
      profundidad)."""
    if _active_orientation_type(context) == "NORMAL":
        return (False, False, True)
    lock = _view_axis_index(context)
    if lock is None:
        return None
    return tuple(i != lock for i in range(3))


def _start_translate(context):
    mask = _translate_mask(context)
    otype = _active_orientation_type(context)
    if mask is None:
        bpy.ops.transform.translate("INVOKE_DEFAULT")
    else:
        # orient_type explícito: la restricción se aplica en la orientación
        # ACTIVA del slot (Local, Normal, personalizada, ...).
        bpy.ops.transform.translate(
            "INVOKE_DEFAULT", constraint_axis=mask, orient_type=otype
        )


def _start_rotate(context):
    otype = _active_orientation_type(context)
    # Con orientación Normal: el eje Z del espacio es la normal de la
    # selección; se resuelve aquí sin necesitar la matriz de la orientación.
    # Se usa constraint_axis (como las teclas X/Y/Z) y no orient_axis: solo
    # constraint_axis activa el sistema de restricciones nativo, que dibuja
    # la guía del eje, muestra el texto en la barra y respeta los pivotes
    # por elemento (Individual Origins).
    if otype == "NORMAL":
        bpy.ops.transform.rotate(
            "INVOKE_DEFAULT", orient_type=otype, constraint_axis=(False, False, True)
        )
        return
    rv3d = getattr(context, "region_data", None)
    mat = _orientation_matrix(context)
    if rv3d is None or mat is None:
        bpy.ops.transform.rotate("INVOKE_DEFAULT")
        return
    # Dirección de la mirada de la cámara en espacio de mundo...
    view_dir = rv3d.view_matrix.inverted_safe().to_3x3() @ Vector((0.0, 0.0, -1.0))
    # ...expresada en el espacio de la orientación activa y snapeada al eje
    # local más frontal (X, Y o Z de esa orientación).
    local_dir = mat.inverted_safe() @ view_dir
    axis = max(range(3), key=lambda i: abs((local_dir.x, local_dir.y, local_dir.z)[i]))
    # Restringir SOLO a ese eje con constraint_axis (mismo sistema que W y
    # las teclas X/Y/Z nativas): guía visual + texto + pivotes correctos.
    constraint = tuple(i == axis for i in range(3))
    bpy.ops.transform.rotate(
        "INVOKE_DEFAULT", orient_type=otype, constraint_axis=constraint
    )


class MODOZ_OT_w_move(bpy.types.Operator):
    """Mover en los ejes de la orientación activa que miran a la vista
    (con Normal, solo a lo largo de la normal)"""

    bl_idname = "modoz.w_move"
    bl_label = "Mover (ejes de vista)"

    @classmethod
    def poll(cls, context):
        return (
            context.area is not None
            and context.area.type == "VIEW_3D"
            and context.region_data is not None
        )

    def invoke(self, context, event):
        _start_translate(context)
        return {"FINISHED"}

    def execute(self, context):
        _start_translate(context)
        return {"FINISHED"}


class MODOZ_OT_e_rotate(bpy.types.Operator):
    """Rotar alrededor del eje de la vista snapeado en la orientación
    activa (con Normal, alrededor de la normal)"""

    bl_idname = "modoz.e_rotate"
    bl_label = "Rotar (eje de vista)"

    @classmethod
    def poll(cls, context):
        return (
            context.area is not None
            and context.area.type == "VIEW_3D"
            and context.region_data is not None
        )

    def invoke(self, context, event):
        _start_rotate(context)
        return {"FINISHED"}

    def execute(self, context):
        _start_rotate(context)
        return {"FINISHED"}


_classes = (MODOZ_OT_w_move, MODOZ_OT_e_rotate)


def register():
    for cls in _classes:
        _state.register_class_safe(cls)


def unregister():
    for cls in reversed(_classes):
        _state.unregister_class_safe(cls)
