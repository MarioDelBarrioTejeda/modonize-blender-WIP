# Backspace = Dissolve contextual (por modo de componentes)

## Objetivo

Enlazar la tecla **Backspace** en Edit Mode de malla a un operador propio que hace
*dissolve* según el modo de componentes activo:

- **modo VÉRTICES**  -> dissolve de vértices (`bpy.ops.mesh.dissolve_verts`).
- **modo ARISTAS**   -> dissolve de aristas (`bpy.ops.mesh.dissolve_edges`).
- **modo POLÍGONOS** -> dissolve de las **aristas interiores de la isla** de caras
  seleccionadas: se eliminan las aristas que comparten **dos caras seleccionadas**
  (y sus vértices internos), conservando el contorno; la isla se fusiona en polígonos
  grandes. NO se toca el contorno.

## Decisiones

- Operador nuevo `modoz.dissolve` (`ModozDissolve`) que ramifica por
  `_state.current_component_mode(context)`.
- FACE se resuelve con bmesh directamente (derivar aristas interiores de las caras
  seleccionadas), en lugar de depender de selección de aristas.
- No existe un `BACK_SPACE` por defecto en el keymap 'Mesh' de esta configuración
  (verificado en Blender: 0 items), así que no se roba tecla; igualmente se añade
  `BACK_SPACE` a la lista de "tecla prestada" de mesh_shortcuts de forma **defensiva**
  (por si otro keyconfig lo usa) y como documentación del reemplazo.

## Contexto (archivos)

- `modonize/editor/mesh_ops.py`
  - Añadir clase `ModozDissolve` (bl_idname `modoz.dissolve`, `bl_options`;
    {"REGISTER","UNDO"}) y registrarla en `_CLASSES`.
  - `poll`: objeto malla activo en Edit Mode.
- `modonize/editor/mesh_shortcuts.py` (`register()`)
  - Añadir `"BACK_SPACE"` al set de `_state.prestada_off(kc, ("Mesh",), {...})`.
  - Añadir `add("BACK_SPACE", "modoz.dissolve")`.
  - No hace falta tocar `unregister` (la prestada_restore y el borrado de items ya
    están genéricos).

## Diseño del operador

`execute` ramifica por modo:

- `VERT`:
  `bpy.ops.mesh.dissolve_verts(use_face_split=False, use_boundary_tear=False)`.
- `EDGE`:
  `bpy.ops.mesh.dissolve_edges(use_verts=True, use_face_split=False)`.
- `FACE`:
  ```
  import bmesh
  bm = bmesh.from_edit_mesh(obj.data)
  bm.edges.ensure_lookup_table()
  # aristas interiores: todas sus caras adyacentes seleccionadas.
  interior = [e for e in bm.edges
              if e.is_manifold and all(f.select for f in e.link_faces)]
  bmesh.ops.dissolve_edges(bm, edges=interior, use_verts=True, use_face_split=False)
  bmesh.update_edit_mesh(obj.data)
  ```
  Si `interior` vacío (p. ej. una sola cara seleccionada), no hace nada (FINISHED).

`bl_description`: "Dissolve contextual: vértices/aristas según el modo, o aristas
interiores de la isla en modo polígono."

## Riesgos

- FACE: disolver aristas interiores fusiona la isla en polígonos grandes; en regiones
  no-manifold o con agujeros puede quedar degradado. Se limita a `is_manifold` para
  evitar bordes raros.
- El `use_verts=True` disuelve también los vértices internos redundantes (merge limpio).
- `bpy.ops.mesh.dissolve_*` son operaciones con undo; el bmesh FACE necesita
  `REGISTER`/`UNDO` para deshacer.
- No se desactiva la tecla Borrar (Del): Backspace solo hace dissolve; Del sigue con el
  menú de borrado por defecto.

## Validación (manual en Blender)

1. Recargar addon; en Edit Mode:
   - Modo VÉRTICES con vértices seleccionados + Backspace -> se fusionan los vértices.
   - Modo ARISTAS con aristas seleccionadas + Backspace -> se disuelven las aristas.
   - Modo POLÍGONOS con una isla de caras seleccionadas + Backspace -> se eliminan las
     aristas interiores y la isla se funde, conservando el contorno.
2. Con una sola cara seleccionada en modo POLÍGONOS no hace nada (ni elimina).
3. Ctrl+Z deshace cada paso.
4. En Object Mode Backspace no afecta.
5. Asegurar que el keymap sigue al desactivar/activar el addon (prestada_restore).
