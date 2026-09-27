# Bevel [B] en tres modos con herramientas nativas de Blender

## Estado: IMPLEMENTADO y confirmado por el usuario

Comportamiento final de la tecla B (operador `modoz.bevel` en
`modonize/editor/mesh_ops.py`), según el modo de selección de componentes:

| Modo    | Comando nativo invocado                                      |
|---------|--------------------------------------------------------------|
| Vertices| `bpy.ops.mesh.bevel("INVOKE_DEFAULT", affect="VERTICES")`    |
| Aristas | `bpy.ops.mesh.bevel("INVOKE_DEFAULT", affect="EDGES")`       |
| Caras   | `bpy.ops.mesh.extrude_region_shrink_fatten("INVOKE_DEFAULT")`|

("Extrude Along Normals", comando del menu Alt+E, verificado en Blender 5.2).

## Decisiones

- Dispatcher minimo `modoz.bevel`: imprescindible para que UNA tecla (B) invoque
  dos operadores nativos distintos segun el modo. No programa geometria.
- `bl_options = set()` y sin propiedades propias: el modal y el redo panel (F9)
  los pone el operador nativo invocado (bevel con "Afectar a" + "Segmentos", o
  el extrude con su configuracion).
- `"INVOKE_DEFAULT"` en los tres: arrastre modal nativo (igual que Ctrl+B y
  Alt+E). El F9 nativo del bevel permite cambiar a vertices estando en aristas.
- Modo del componente: `_state.current_component_mode(context)` (helper nuevo en
  `_state.py`, reutilizado por `operator_cycle._current_mode`).
- Fallback bevel sin `affect` para Blender < 3.2.
- El addon instalado en Blender es un SYMLINK al repo
  (`~/.config/blender/5.2/scripts/addons/modonize -> .../modonize-blender-WIP/modonize`),
  los cambios llegan directos; basta recargar el addon.

## Riesgos y notas

- Modal anidado desde `execute` de otro operador: patron estandar (el bevel
  nativo y el extrude del Alt+E son modales). Invocarlos desde el MCP corta la
  conexion puente (confirmado); por teclado en Blender es el comportamiento
  normal con arrastre del raton.
- El crash de Poliigon detectado durante la sesion es de un addon externo, no
  relacionado; no se toca.

## Validacion

1. Sintaxis: `python3 -m py_compile modonize/editor/mesh_ops.py` (OK).
2. Recargar addon: Prefs -> Addons -> Modonize off/on.
3. Probar con B en Edit Mode: vertices -> bevel de vertices; aristas -> bevel de
   aristas (F9 puede cambiarlo a vertices); caras -> arrastre hacia las normales.
