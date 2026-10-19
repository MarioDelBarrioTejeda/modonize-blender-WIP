# W dos veces → Vertex/Edge Slide ("railes")

## Objetivo

Que al pulsar **W dos veces** durante un movimiento activo con W, el transform conmuta a
**Vertex Slide / Edge Slide** (desplazarse por las aristas conectadas, los "railes"),
replicando el comportamiento del **G-G nativo** de Blender. W-W-W vuelve a Move.

## Mecanismo verificado (fuente de Blender, `transform.cc`)

- El G-G nativo **no** es un repeat de operador: el segundo G se procesa **durante el
  modal** del transform mediante el keymap **"Transform Modal Map"**, con items
  `G → TFM_MODAL_VERT_EDGE_SLIDE` y `G → TFM_MODAL_TRANSLATE`.
- El conmutador de modo lo filtra el `poll_modal_item` nativo:
  - item `VERT_EDGE_SLIDE`: activo solo durante TRANSLATION y en mallas (Mesh/MeshUV);
  - item `TRANSLATE`: activo solo cuando el modo actual **no** es translate.
  → Con ambos items en W, W-W alterna mover↔slide automáticamente (igual que G-G-G).
- La API de Python lo soporta: `KeyMapItems.new_modal(propvalue, type, value)`.
- Solo aplica en modo inmediato (`transform_immediate=True`), donde W = `transform.translate`.

## Cambios

Un solo archivo: **`modonize/transform/tools.py`**

1. En `register()` (tras el guard de `enable_transform`), si `prefs.transform_immediate`:
   - `km = kc.keymaps.get("Transform Modal Map")` (None-check, como el resto del módulo).
   - `km.keymap_items.new_modal("VERT_EDGE_SLIDE", "W", "PRESS")`
   - `km.keymap_items.new_modal("TRANSLATE", "W", "PRESS")`
   - Guardar ambos `(km, kmi)` en la lista `_addon_keymaps` existente; `unregister()`
     ya la recorre y los elimina, así que no hay código de limpieza nuevo.
2. Actualizar el docstring del módulo: documentar que W-W conmuta a Vertex/Edge Slide.

## Fuera de alcance / no se toca

- Items nativos G/R/S del Transform Modal Map: intactos.
- Tool mode (`transform_immediate=False`): sin cambios.
- Paridad E/R (E→rotate, R→resize dentro del modal): descartada por decisión del usuario.
- Shift-R (repeat last) y flujos numéricos: sin cambios.

## Riesgos

- Bajo: 2 items modales; el filtrado por contexto/modo lo hace el poll nativo de Blender.
- Limpieza al desactivar: los items se eliminan en `unregister()` (mismo patrón que el resto).
- Keymap personalizado por el usuario: nuestros items se suman, no pisan nada.

## Validación en Blender

1. Recargar el addon (desactivar/activar en Preferencias → Add-ons).
2. Edit Mode, 1 vértice: W, mover, **W** → Vertex Slide por las aristas conectadas; **W** otra vez → vuelve a Move.
3. Seleccionar una arista: W-W → Edge Slide.
4. Esc cancela; G-G nativo sigue comportándose igual.
5. Object Mode o nodo editor: W durante un translate activo no hace nada (poll desactiva el slide fuera de malla), igual que G nativo.
