# SPDX-License-Identifier: GPL-2.0-or-later

"""Operadores auxiliares de edición de malla (usados por las teclas [B], [L], etc.)."""

import bmesh
import mathutils
import bpy
from bpy_extras import view3d_utils

from .. import _state


class ModozSelectLoop(bpy.types.Operator):
    bl_idname = "modoz.select_loop"
    bl_label = "Seleccionar loop de aristas"
    bl_description = "Selecciona el edge loop alrededor de la arista activa."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"

    def execute(self, context):
        try:
            if hasattr(bpy.ops.mesh, "select_edge_loop_multi"):
                bpy.ops.mesh.select_edge_loop_multi()
            else:
                bpy.ops.mesh.loop_multi_select(ring=False)
            return {"FINISHED"}
        except Exception:
            return {"CANCELLED"}


class ModozInsetDepth(bpy.types.Operator):
    bl_idname = "modoz.inset_depth"
    bl_label = "Inset (Modonize)"
    bl_description = (
        "Inset sobre la selección unida. Arrastra el ratón para ajustar la "
        "Depth (profundidad a lo largo de las normales) y usa la rueda para el "
        "grosor del borde. Clic o Return confirma; Esc o botón derecho cancela."
    )
    bl_options = {"REGISTER", "UNDO"}

    # Estado de instancia (valores por defecto para invocaciones directas).
    _obj = None
    _snap = None
    _base = None
    _depth = 0.0
    _unit = 1.0

    thickness: bpy.props.FloatProperty(
        name="Grosor",
        description="Grosor del borde de inset",
        default=0.0,
        min=0.0,
        soft_min=0.0,
        unit="LENGTH",
        options={"SKIP_SAVE"},
    )
    depth: bpy.props.FloatProperty(
        name="Depth",
        description="Profundidad a lo largo de las normales",
        default=0.0,
        unit="LENGTH",
        options={"SKIP_SAVE"},
    )
    individual: bpy.props.BoolProperty(
        name="Individual",
        description=(
            "Inserta cada cara por separado; la Depth se aplica a cada cara "
            "según su propia normal"
        ),
        default=False,
        options={"SKIP_SAVE"},
    )
    even: bpy.props.BoolProperty(
        name="Offset Even",
        description="Grosor de borde uniforme a lo largo de las aristas",
        default=True,
        options={"SKIP_SAVE"},
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            obj is not None
            and obj.type == "MESH"
            and obj.mode == "EDIT"
            and _state.current_component_mode(context) == "FACE"
        )

    # -- ciclo de vida -------------------------------------------------------

    def invoke(self, context, event):
        obj = context.active_object
        if obj is None or obj.type != "MESH" or obj.mode != "EDIT":
            return {"CANCELLED"}
        if _state.current_component_mode(context) != "FACE":
            return {"CANCELLED"}
        if not self._start(context, obj):
            self.report({"INFO"}, "Inset: no hay caras seleccionadas")
            return {"CANCELLED"}
        if not self._rebuild(self.thickness, 0.0):
            self._cleanup()
            return {"CANCELLED"}
        self._start_mouse = (event.mouse_region_x, event.mouse_region_y)
        context.window_manager.modal_handler_add(self)
        self._header(context)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        # Camino no interactivo (redo F9 / invocación directa). No reutiliza
        # ningún estado almacenado (_obj/_snap/_base): al hacer redo, Blender
        # revierte la escena y anula las referencias RNA guardadas. Aquí se
        # opera fresco sobre el objeto activo y la selección actual.
        obj = context.active_object
        if obj is None or obj.type != "MESH" or obj.mode != "EDIT":
            return {"CANCELLED"}
        if _state.current_component_mode(context) != "FACE":
            return {"CANCELLED"}
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.normal_update()
        faces = [f for f in bm.faces if f.select]
        if not faces:
            self.report({"INFO"}, "Inset: no hay caras seleccionadas")
            return {"CANCELLED"}
        if self.individual:
            bmesh.ops.inset_individual(
                bm,
                faces=faces,
                use_even_offset=self.even,
                thickness=self.thickness,
                depth=self.depth,
            )
        else:
            bmesh.ops.inset_region(
                bm,
                faces=faces,
                use_boundary=True,
                use_even_offset=self.even,
                thickness=self.thickness,
                depth=self.depth,
            )
        bmesh.update_edit_mesh(obj.data)
        return {"FINISHED"}

    def modal(self, context, event):
        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._restore()
            self._cleanup(context)
            return {"CANCELLED"}

        if (event.type == "LEFTMOUSE" and event.value == "RELEASE") or (
            event.type in {"RETURN", "NUMPAD_ENTER"} and event.value == "PRESS"
        ):
            # El redo F9 lo resuelve execute() con una operación fresca, así
            # que aquí sí se libera el snapshot.
            self._cleanup(context)
            return {"FINISHED"}

        if event.type == "MOUSEMOVE":
            self._apply_depth(self._depth_from_mouse(context, event))
            self._header(context)
        elif event.type == "WHEELUPMOUSE" and event.value == "PRESS":
            self.thickness += self._unit * 0.05
            self._rebuild(self.thickness, self._depth)
            self._header(context)
        elif event.type == "WHEELDOWNMOUSE" and event.value == "PRESS":
            self.thickness = max(0.0, self.thickness - self._unit * 0.05)
            self._rebuild(self.thickness, self._depth)
            self._header(context)
        return {"RUNNING_MODAL"}

    def __del__(self):
        # Limpia el snapshot si el operador se descarta (evita mallas huérfanas).
        snap = getattr(self, "_snap", None)
        if snap is not None:
            try:
                bpy.data.meshes.remove(snap)
            except Exception:
                pass
            self._snap = None

    # -- preparación ---------------------------------------------------------

    def _start(self, context, obj):
        """Captura snapshot, geometría de referencia y grosor por defecto."""
        mesh = obj.data
        # Fuerza el flush del edit bmesh -> mesh: la topología/geometría aún no
        # sincronizada (p. ej. tras subdividir en Edit Mode) debe quedar en el
        # snapshot. Sin esto, obj.data.copy() captura un estado obsoleto.
        try:
            obj.update_from_editmode()
        except Exception:
            pass
        bm = bmesh.from_edit_mesh(mesh)
        faces = [f for f in bm.faces if f.select]
        if not faces:
            return False
        bm.normal_update()

        # Grosor por defecto: ~10% de la longitud de arista media de la selección.
        seen = set()
        total = 0.0
        count = 0
        for f in faces:
            for e in f.edges:
                if id(e) in seen:
                    continue
                seen.add(id(e))
                total += e.calc_length()
                count += 1
        avg = (total / count) if count else 1.0
        self._unit = max(avg, 1e-4)
        if self.thickness <= 0.0:
            self.thickness = max(avg * 0.1, 1e-4)

        # Normal media de la selección (local) y su escala en el mundo.
        n = mathutils.Vector((0.0, 0.0, 0.0))
        for f in faces:
            n += f.normal
        if n.length < 1e-9:
            n = faces[0].normal.copy()
        n.normalize()
        self._avg_normal_local = n
        m3 = obj.matrix_world.to_3x3()
        nm = m3.inverted_safe().transposed() @ n
        self._normal_scale = nm.length if nm.length > 1e-9 else 1.0
        self._avg_normal_world = nm.normalized() if nm.length > 1e-9 else n.copy()
        self._pivot_local = (
            sum((f.calc_center_median() for f in faces), mathutils.Vector()) / len(faces)
        )
        self._pivot_world = obj.matrix_world @ self._pivot_local

        self._obj = obj
        self._snap = mesh.copy()
        self._depth = 0.0
        self._base = []
        return True

    # -- geometría -----------------------------------------------------------

    def _rebuild(self, thickness, depth):
        """Rehace el inset desde el snapshot con el grosor dado y aplica depth."""
        if self._obj is None or self._snap is None:
            return False
        bm = bmesh.from_edit_mesh(self._obj.data)
        bm.clear()
        bm.from_mesh(self._snap)
        bm.verts.ensure_lookup_table()
        bm.normal_update()
        faces = [f for f in bm.faces if f.select]
        if not faces:
            return False
        # Las caras de entrada siguen siendo la región interna tras el inset.
        if self.individual:
            bmesh.ops.inset_individual(
                bm,
                faces=faces,
                use_even_offset=self.even,
                thickness=thickness,
                depth=0.0,
            )
        else:
            bmesh.ops.inset_region(
                bm,
                faces=faces,
                use_boundary=True,
                use_even_offset=self.even,
                thickness=thickness,
                depth=0.0,
            )
        bm.normal_update()
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        # Se guardan ÍNDICES (no referencias): la malla del bmesh se recrea
        # entre eventos del modal y las referencias BMVert quedarían muertas.
        # En modo individual la Depth usa la normal de cada cara; en modo
        # región, la normal por vértice (empuje unido).
        base = []
        seen = set()
        for f in faces:
            f_normal = f.normal.copy() if self.individual else None
            for v in f.verts:
                if v.index in seen:
                    continue
                seen.add(v.index)
                n = f_normal if self.individual else v.normal
                base.append((v.index, v.co.copy(), n.copy()))
        for idx, co, n in base:
            bm.verts[idx].co = co + n * depth
        # Al mover la cara interior se crean caras laterales no-coplanares cuyo
        # winding quedó invertido: reorienta las normales hacia fuera.
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.update_edit_mesh(self._obj.data)
        self._base = base
        self._depth = depth
        self.depth = depth  # el F9 conserva la Depth arrastrada
        return True

    def _apply_depth(self, depth):
        self._depth = depth
        self.depth = depth  # el F9 conserva la Depth arrastrada
        if not self._base or self._obj is None:
            return
        bm = bmesh.from_edit_mesh(self._obj.data)
        bm.verts.ensure_lookup_table()
        nverts = len(bm.verts)
        for idx, co, n in self._base:
            if 0 <= idx < nverts:
                bm.verts[idx].co = co + n * depth
        # Reorienta las normales tras el movimiento de la Depth (caras del
        # borde del inset dejan de ser coplanares y podrían quedar invertidas).
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.update_edit_mesh(self._obj.data)

    def _restore(self):
        if self._obj is None or self._snap is None:
            return
        bm = bmesh.from_edit_mesh(self._obj.data)
        bm.clear()
        bm.from_mesh(self._snap)
        bmesh.update_edit_mesh(self._obj.data)

    def _depth_from_mouse(self, context, event):
        region = context.region
        rv3d = context.region_data
        if region is None or rv3d is None:
            return self._depth
        cur = view3d_utils.region_2d_to_location_3d(
            region, rv3d, (event.mouse_region_x, event.mouse_region_y), self._pivot_world
        )
        start = view3d_utils.region_2d_to_location_3d(
            region, rv3d, self._start_mouse, self._pivot_world
        )
        world_depth = (cur - start).dot(self._avg_normal_world)
        return world_depth / self._normal_scale

    # -- utilidades ----------------------------------------------------------

    def _header(self, context):
        if getattr(context, "area", None) is None:
            return
        context.area.header_text_set(
            f"Inset (Modo)  grosor: {self.thickness:.3f}  depth: {self._depth:.3f}"
        )

    def _cleanup(self, context=None, free=True):
        if context is not None and getattr(context, "area", None) is not None:
            context.area.header_text_set(None)
        self._base = []
        if free and self._snap is not None:
            try:
                bpy.data.meshes.remove(self._snap)
            except Exception:
                pass
            self._snap = None


class ModozBevel(bpy.types.Operator):
    bl_idname = "modoz.bevel"
    bl_label = "Bevel (Modonize)"
    bl_description = (
        "Lanza la herramienta nativa de Blender según el modo de selección: "
        "bevel (vértices o aristas) según el modo, o inset unido con Depth "
        "(arrastra: Depth, rueda: grosor) en modo polígono."
    )
    # Sin REGISTER y sin propiedades propias: el redo panel (F9) y el modal
    # los pone el operador nativo invocado (bevel) o modoz.inset_depth, que es
    # el que entra en la pila de undo/redo.
    bl_options = set()

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"

    def execute(self, context):
        mode = _state.current_component_mode(context)
        if mode == "FACE":
            # Modo polígono: inset modal propio. El ratón controla la Depth
            # (como el Ctrl del inset nativo) y la rueda el grosor del borde.
            bpy.ops.modoz.inset_depth("INVOKE_DEFAULT")
            return {"FINISHED"}

        # Modos vértice y arista: bevel nativo de Blender con su configuración
        # (afectar a vértices o aristas), lanzado en modo modal (INVOKE_DEFAULT)
        # igual que el Ctrl+B de serie: arrastras para ajustar y confirmas con
        # clic. El F9 del propio bevel ofrece luego "Afectar a: Vértices/
        # Aristas", "Segmentos", etc.
        affect = "VERTICES" if mode == "VERT" else "EDGES"
        try:
            bpy.ops.mesh.bevel("INVOKE_DEFAULT", affect=affect)
        except Exception:
            # Blender < 3.2: bevel sin 'affect' (infiere del modo visual).
            bpy.ops.mesh.bevel("INVOKE_DEFAULT")
        return {"FINISHED"}


_CLASSES = (ModozSelectLoop, ModozInsetDepth, ModozBevel)


def register():
    for cls in _CLASSES:
        _state.register_class_safe(cls)


def unregister():
    for cls in reversed(_CLASSES):
        _state.unregister_class_safe(cls)
