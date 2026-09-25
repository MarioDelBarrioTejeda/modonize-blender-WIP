# Modonize Blender

Se trata de un complemento para blender que pretende llevar la experiencia de usuario de Luxology Modo a Blender, poniendo especial foco en el modelado.

## Características

### Sistema de Seleccion

- En el modo edición de mallas se emplea la tecla [space] para alternar entre modos de selección de componentes [ vértices , mallas , caras]. 

- Cada uno de esos modos de componente se mantendrá la sección ultima en ese estado. 

> De tal manera que si en modo caras seleccionas una cara, cambias a aristas y seleccionas una arista ajena a la anterior sección, cuando vuelvas al modo caras veras la selección de la cara pero no de la arista, si luego vas al modo arista no se vera la cara seleccionada pero si la arista

- Al hacer doble clic en **modo aristas**  sobre una arista se seleccionará todo el *loop* la arista 

- Al hacer doble clic en **modo vértices**  sobre un vértice se seleccionará toda la malla unida a ese vértice

- Al hacer doble clic en **modo aristas** sobre una arista se seleccionará toda la malla unida a esa arista

- selececionar previus y next [DOWN_ARROW] y [UP_ARROW]

- selececionar more y less [SHIFT+DOWN_ARROW] y [SHIFT+UP_ARROW]

### Sistema de Transformación

Se cambian los atajos de trasformación por los estandares en la industria [W,E,R]. Se cambia en todo el contexto de Blender: *Dopesheet*, *Curves* y *Animation* para mover y escalar *keys*, *geometry nodes* y *shader materials* para mover y escalar nodos.

#### Move

- Atajo [W]

Cambia la herramienta de mover, es muy similar a la versión de Blender con la diferencia de que si pinchas y arrastras en cualquier lugar de la vista que no sean los manipuladores de *gidmo* se moverá el los dos ejes contrarios al eje desde el que estes mirando.

#### Rotate

- Atajo [E]

Cambia la herramienta de rotar, es muy similar a la versión de Blender con la diferencia de que si pinchas y arrastras en cualquier lugar de la vista que no sea el *gidmo* se rotará el mismo eje desde el que estas mirando.

#### escalar

- Atajo [R]

Cambia la herramienta de rotar, es muy similar a la versión de Blender con la diferencia de que si pinchas y arrastras en cualquier lugar de la vista que no sea el *gidmo* se rotará el mismo eje desde el que estas mirando.

### Bevel

- Atajo [B]

- El viselado funcionara como un *extrude* + *inset* en **modo poligono**

- Como *bevel* de vertices en **modo vertices**

- 

### Otros atajos

- [F] para hacer foco en la vista 3D y UV sobre la selecion de mallas u objetos, centrar el foco en el ouliner en la selección ,  centrar la vista sobre la la seleccion de nodos etc ...
- [L] para selecionar loops
- [D] subdividir malla
- 
