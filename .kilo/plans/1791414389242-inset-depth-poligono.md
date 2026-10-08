# Bevel de polígono -> Inset con Depth modal

## Objetivo

En modo polígono (FACE), sustituir el inset modal nativo actual por un operador modal
propio (`modoz.inset_depth`) que crea el borde de inset sobre la selección **unida** y
permite:

- arrastrar el ratón -> **Depth** (equivalente al Ctrl del inset nativo),
- rueda del ratón -> **grosor** (thickness) del borde,
- LMB/Return confirmar; RMB/Esc cancelar restaurando la geometría.

Los modos vértice/arista (bevel nativo) no cambian.

## Decisiones

- Opción A (operador modal propio). Viable: `bmesh.ops.inset_region` expone `thickness` y
  `depth`, y el repo ya tiene patrón modal en `modonize/transform/drag_ops.py`.
- Arrastre = Depth; rueda = grosor (elección del usuario).
- Sin dependencias del SO (se descarta inyectar un Ctrl sintético) ni APIs no públicas.
- Alcance v1: **objeto activo** en Edit Mode. Multi-objeto (varios meshes en edit) queda
  fuera de alcance (ver Riesgos).

## Contexto (archivos y líneas)

- `modonize/editor/mesh_ops.py`
  - `ModozBevel.execute()` rama FACE (~líneas 50-56): hoy llama a `_inset()`.
  - `_inset()` (~líneas 71-75): hoy `bpy.ops.mesh.inset("INVOKE_DEFAULT")`. Se reemplaza.
  - `_CLASSES` (~línea 76): lista de clases a registrar (registro vía
    `_state.register_class_safe`).
  - `bl_description` de `ModozBevel` (~líneas 35-39).
- `modonize/editor/__init__.py`: `mesh_ops.register()` ya recorre `_CLASSES`; no requiere
  cambios.
- `modonize/keymaps.py` / `modonize/editor/mesh_shortcuts.py`: [B] ya apunta a
  `modoz.bevel`; **sin cambios**.
- `especificaciones.md`: ya documenta "inset con Depth" para polígono.
- Patrón de referencia modal: `modonize/transform/drag_ops.py` (invoke -> modal_handler_add
  -> modal; ESC/RIGHTMOUSE cancel con restore; LEFTMOUSE RELEASE finish;
  `context.area.header_text_set`).

## Diseño: operador `ModozInsetDepth`

- `bl_idname = "modoz.inset_depth"`, `bl_options = {"REGISTER", "UNDO"}`.
- Propiedades `bpy.props.FloatProperty`: `thickness` y `depth` (para redo/fallback y para
  el panel redo).
- `poll`: Edit Mode sobre mesh y modo de componente FACE activo
  (`_state.current_component_mode(context) == "FACE"`).

Estado de instancia (definido en `invoke`):

- `self._obj`: objeto activo.
- `self._snap`: copia de la malla pre-operación (`obj.data.copy()`), base para rebuild y
  para restaurar al cancelar. Conserva topología y flags de selección.
- `self._thickness`: grosor actual (se inicializa con un valor por defecto razonable).
- `self._depth`: profundidad actual (0 al entrar).
- `self._inner`: lista de `(vert, co_inicial, normal_local)` de los vértices internos del
  inset (para aplicar depth sin recrear topología).
- `self._start_mouse`: posición inicial del ratón.
- `self._pivot_world` y `self._avg_normal_world`: pivote y normal media (mundo) de la
  selección, para proyectar el movimiento del ratón.

Métodos:

- `_rebuild(thickness, depth)`:
  1. `bm = bmesh.from_edit_mesh(obj.data)`; `bm.clear()`; `bm.from_mesh(self._snap)`
     (restaura geometría y selección originales).
  2. `faces = [f for f in bm.faces if f.select]`.
  3. `res = bmesh.ops.inset_region(bm, faces=faces, use_boundary=True,
     use_even_offset=True, thickness=thickness, depth=0.0)`.
  4. Guardar `self._inner` a partir de los vértices del resultado (`res["faces"]`), con su
     `co` y `normal` actuales (pre-depth).
  5. `_apply_depth(depth)` y `bmesh.update_edit_mesh(obj.data)`.
- `_apply_depth(depth)`: para cada `(v, co, n)` -> `v.co = co + n * depth`;
  `bmesh.update_edit_mesh`.
- `_restore_snapshot()`: `bm.clear(); bm.from_mesh(self._snap); bmesh.update_edit_mesh`.
- `invoke(context, event)`:
  - validar caras seleccionadas; si vacío -> `self.report({"INFO"}, ...)`; CANCELLED.
  - crear `self._snap`, capturar mouse/pivote/normal media, `self._depth = 0`.
  - `_rebuild(self._thickness, 0.0)`.
  - `context.window_manager.modal_handler_add(self)`; header; RUNNING_MODAL.
- `modal(context, event)`:
  - ESC / RIGHTMOUSE PRESS -> `_restore_snapshot()`, liberar `_snap`, header None,
    CANCELLED.
  - LEFTMOUSE RELEASE o RETURN -> liberar `_snap`, header None, FINISHED.
  - MOUSEMOVE -> calcular desplazamiento mundo del ratón (`view3d_utils.
    region_2d_to_location_3d` con `self._pivot_world`, patrón drag_ops) y proyectarlo
    sobre `self._avg_normal_world`; `self._depth = proyección`; `_apply_depth`; header.
  - WHEELUPMOUSE / WHEELDOWNMOUSE -> `self._thickness +=/-= paso`;
    `_rebuild(self._thickness, self._depth)`; header.
  - return RUNNING_MODAL.
- `execute(context)` (fallback/redo): aplicar no interactivamente con las props actuales
  sobre la selección actual; si `self._snap` existe, reusarlo para rebuild. Sin
  `_snap` (redó tras cerrar sesión), aplicar `inset_region` directo sin baseline.
- Header: p. ej. `f"Inset (Modo)  grosor: {thickness:.3f}  depth: {depth:.3f}"`.

## Pasos de implementación

1. En `modonize/editor/mesh_ops.py`: añadir la clase `ModozInsetDepth` con lo anterior y
   registrarla en `_CLASSES`.
2. Cambiar la rama FACE de `ModozBevel.execute()` a
   `bpy.ops.modoz.inset_depth("INVOKE_DEFAULT")` y devolver FINISHED; eliminar
   `_inset()`.
3. Actualizar `bl_description` de `ModozBevel` (ya menciona "inset (con Depth)";
   ajustar a que el ratón controla Depth y la rueda el grosor).
4. Actualizar el comentario del operador sobre el panel redo para reflejar el nuevo
   operador (`modoz.inset_depth`).

## Riesgos

- Rendimiento: `_rebuild` (re-ejecuta `inset_region`) solo en la rueda, no en cada
  MOUSEMOVE; el mousemove solo mueve vértices. Aceptable en mallas medianas.
- Coordenadas: el depth se aplica en espacio local con normales locales; con escalas no
  uniformes del objeto puede ser aproximado. Documentar.
- Cancelación: se apoya en `obj.data.copy()` + `bm.from_mesh`; verificar que la copia
  conserva los flags de selección de polígonos.
- Redo/undo: Ctrl+Z funciona vía `UNDO`; el panel F9 (redo) es best-effort (puede quedar
  aproximado tras cerrar la sesión).
- Multi-objeto: no soportado en v1 (solo objeto activo). Si hay varios meshes en edit,
  solo se edita el activo.

## Validación (manual en Blender)

1. Edit Mode, modo FACE, seleccionar caras, pulsar [B]: aparece el borde de inset; el
   arrastre vertical modifica la Depth.
2. La rueda modifica el grosor; el header muestra ambos valores.
3. LMB confirma; Ctrl+Z revierte el paso.
4. RMB/Esc cancela y deja la malla exactamente igual (topología y coordenadas).
5. Sin caras seleccionadas: no crashea, muestra INFO.
6. Modos VERT y EDGE siguen lanzando el bevel nativo sin cambios.
